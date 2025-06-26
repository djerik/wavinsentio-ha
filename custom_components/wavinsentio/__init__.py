import logging

from homeassistant import config_entries, core

from homeassistant.exceptions import ConfigEntryAuthFailed, Unauthorized

from .const import DOMAIN, CONF_DEVICE_NAME

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from wavinsentio.wavinsentio import Device, Room, WavinSentio, UnauthorizedException

from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["climate", "sensor", "switch"]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
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


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Wavin Sentio component."""
    # @TODO: Add setup code.
    return True


class WavinSentioDataCoordinator(DataUpdateCoordinator):
    """Get and update the latest data."""

    def __init__(self, hass, api:WavinSentio, device_name):
        super().__init__(
            hass,
            _LOGGER,
            name="WavinSentioData",
            update_interval=timedelta(seconds=120),
        )
        self.api = api
        self.device_name = device_name
        self.roomdata = None
        self.location = None

    async def _async_update_data(self):
        try:

            #self.roomdata = await self.hass.async_add_executor_job(
#                self.api.get_rooms, self.location_id
            #)

            self._device = await self.hass.async_add_executor_job(
                self.api.get_device, self.device_name
            )
        except KeyError as ex:
            raise UpdateFailed("Problems calling Wavin Sentio") from ex

    def get_device(self) -> Device:
        return self._device

    def get_rooms(self):
        return self.get_device().lastConfig.sentio.rooms

    def get_room(self, id) -> Room:
        for room in self.get_device().lastConfig.sentio.rooms:
            if room.id == id:
                return room
        return None

    def set_new_temperature(self, code, temperature):
        _LOGGER.debug("Setting temperature: %s", temperature)
        return self.hass.async_add_executor_job(
            self.api.set_temperature, code, temperature
        )

    def set_new_profile(self, code, profile):
        _LOGGER.debug("Setting profile: %s", profile)
        self.hass.async_add_executor_job(self.api.set_profile, code, profile)

    def turn_on_standby(self):
        self.hass.async_add_executor_job(self.api.turn_on_standby, self.location_id)

    def turn_off_standby(self):
        self.hass.async_add_executor_job(self.api.turn_off_standby, self.location_id)

    def get_device(self) -> Device:
        return self._device
