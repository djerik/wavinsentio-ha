"""Wavin Sentio integration for Home Assistant."""

from datetime import timedelta
import logging

from homeassistant import config_entries, core
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from wavinsentio.wavinsentio import (
    Device,
    HCMode,
    Room,
    StandbyMode,
    UnauthorizedException,
    VacationMode,
    WavinSentio,
    WavinSentioException,
)

from .const import CONF_DEVICE_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["binary_sensor", "climate", "sensor", "switch", "datetime", "select"]

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up Wavin Sentio from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        api = await hass.async_add_executor_job(
            WavinSentio, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
        )
    except UnauthorizedException as err:
        raise ConfigEntryAuthFailed(err) from err
    except WavinSentioException as err:
        raise ConfigEntryNotReady(err) from err

    coordinator = WavinSentioDataCoordinator(hass, api, entry.data[CONF_DEVICE_NAME])
    hass.data[DOMAIN]["coordinator" + entry.data[CONF_DEVICE_NAME]] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unloading a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop("coordinator" + entry.data[CONF_DEVICE_NAME], None)
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
            device = await self.hass.async_add_executor_job(
                self.api.get_device, self.device_name
            )
        except UnauthorizedException as ex:
            raise ConfigEntryAuthFailed(ex) from ex
        except (WavinSentioException, KeyError, ValueError) as ex:
            raise UpdateFailed(f"Problems calling Wavin Sentio: {ex}") from ex
        # The cloud occasionally answers without the device configuration. Treat
        # that as a failed update instead of exposing an empty device.
        if not device.lastConfig.sentio.rooms:
            raise UpdateFailed("Wavin Sentio returned no configuration for the device")
        self._device = device

    async def _async_send(self, func, *args):
        """Send a change to the Wavin cloud and report a failure to the user."""
        try:
            return await self.hass.async_add_executor_job(func, *args)
        except WavinSentioException as ex:
            raise HomeAssistantError(f"Wavin Sentio did not accept the change: {ex}") from ex

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
        return self._async_send(self.api.set_temperature, self.device_name, room_id, temperature
        )

    def set_new_profile(self, code, profile):
        """Set a new profile for the specified code."""
        _LOGGER.debug("Setting profile: %s", profile)
        return self._async_send(self.api.set_profile, code, profile)

    def turn_on_standby(self):
        """Turn on standby mode for the device."""
        return self._async_send(self.api.set_standby_mode, self.device_name, StandbyMode.STANDBY_MODE_ON)

    def turn_off_standby(self):
        """Turn off standby mode for the device."""
        return self._async_send(self.api.set_standby_mode, self.device_name, StandbyMode.STANDBY_MODE_OFF)

    def set_hc_mode(self, hc_mode: HCMode):
        """Set the heating/cooling mode for the device."""
        _LOGGER.debug("Setting HC mode: %s", hc_mode)
        return self._async_send(self.api.set_HC_mode, self.device_name, hc_mode.value)

    def turn_on_vacation_mode_device(self):
        """Turn on vacation mode for the device."""
        return self._async_send(self.api.set_vacation_mode, self.device_name, VacationMode.VACATION_MODE_ON)

    def turn_off_vacation_mode_device(self):
        """Turn off vaction mode for the device."""
        return self._async_send(self.api.set_vacation_mode, self.device_name, VacationMode.VACATION_MODE_OFF)

    def turn_on_vacation_mode_room(self, room_id: int):
        """Turn on vacation mode for the room."""
        return self._async_send(self.api.set_vacation_mode_room, self.device_name, room_id, VacationMode.VACATION_MODE_ON)

    def turn_off_vacation_mode_room(self, room_id: int):
        """Turn off vacation mode for the room."""
        return self._async_send(self.api.set_vacation_mode_room, self.device_name, room_id, VacationMode.VACATION_MODE_OFF)

    def set_vacation_mode_until(self, value):
        """Set the vacation mode until value."""
        _LOGGER.debug("Setting vacation mode until: %s", value)
        return self._async_send(self.api.set_vacation_mode_until, self.device_name, value)

