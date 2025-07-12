"""Wavin Sentio integration for Home Assistant."""

from datetime import timedelta
import logging

from homeassistant import config_entries, core
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from wavinsentio.wavinsentio import (
    Device,
    Room,
    StandbyMode,
    UnauthorizedException,
    WavinSentio,
)

from .const import CONF_DEVICE_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["climate", "sensor", "switch"]

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up Wavin Sentio from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        api = await hass.async_add_executor_job(
            WavinSentio, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
        )
    except UnauthorizedException as err:
        raise ConfigEntryAuthFailed(err) from err

    coordinator = WavinSentioDataCoordinator(hass, api, entry.data[CONF_DEVICE_NAME])
    hass.data[DOMAIN]["coordinator" + entry.data[CONF_DEVICE_NAME]] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unloading a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Wavin Sentio component."""
    # @TODO: Add setup code.
    return True


class WavinSentioDataCoordinator(DataUpdateCoordinator):
    """Get and update the latest data."""

    def __init__(self, hass: core.HomeAssistant, api: WavinSentio, device_name) -> None:
        """Initialize the WavinSentioDataCoordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="WavinSentioData",
            update_interval=timedelta(seconds=120),
        )
        self.api = api
        self.device_name = device_name
        self._device = None

    async def _async_update_data(self):
        try:
            self._device = await self.hass.async_add_executor_job(
                self.api.get_device, self.device_name
            )
        except KeyError as ex:
            raise UpdateFailed("Problems calling Wavin Sentio") from ex

    def get_device(self) -> Device:
        """Return the current device."""
        return self._device

    def get_rooms(self):
        """Return all rooms for the current device."""
        return self.get_device().lastConfig.sentio.rooms

    def get_room(self, id) -> Room:
        """Return the room with the specified id, or None if not found."""
        for room in self.get_device().lastConfig.sentio.rooms:
            if room.id == id:
                return room
        return None

    def set_new_temperature(self, room_id, temperature):
        """Set a new temperature for the specified room."""
        _LOGGER.debug("Setting temperature: %s", temperature)
        return self.hass.async_add_executor_job(
            self.api.set_temperature, self.device_name, room_id, temperature
        )

    def set_new_profile(self, code, profile):
        """Set a new profile for the specified code."""
        _LOGGER.debug("Setting profile: %s", profile)
        self.hass.async_add_executor_job(self.api.set_profile, code, profile)

    def turn_on_standby(self):
        """Turn on standby mode for the device."""
        self.hass.async_add_executor_job(self.api.set_standby_mode, self.device_name, StandbyMode.STANDBY_MODE_ON)

    def turn_off_standby(self):
        """Turn off standby mode for the device."""
        self.hass.async_add_executor_job(self.api.set_standby_mode, self.device_name, StandbyMode.STANDBY_MODE_OFF)
