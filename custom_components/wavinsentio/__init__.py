import logging

from homeassistant import config_entries, core

from homeassistant.exceptions import ConfigEntryAuthFailed, Unauthorized

from .const import DOMAIN, CONF_LOCATION_ID

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from wavinsentio.wavinsentio import WavinSentio, UnauthorizedException

from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["climate", "sensor", "switch"]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    hass.data.setdefault(DOMAIN, {})

    try:
        api = await hass.async_add_executor_job(
            WavinSentio, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )
    except UnauthorizedException as err:
        raise ConfigEntryAuthFailed(err) from err

    coordinator = WavinSentioDataCoordinator(hass, api, entry.data[CONF_LOCATION_ID])
    hass.data[DOMAIN]["coordinator" + entry.data[CONF_LOCATION_ID]] = coordinator

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

    def __init__(self, hass, api, location_id):
        super().__init__(
            hass,
            _LOGGER,
            name="WavinSentioData",
            update_interval=timedelta(seconds=120),
        )
        self.api = api
        self.location_id = location_id
        self.roomdata = None
        self.location = None

    async def _async_update_data(self):
        try:
            self.roomdata = await self.hass.async_add_executor_job(
                self.api.get_rooms, self.location_id
            )

            self.location = await self.hass.async_add_executor_job(
                self.api.get_location, self.location_id
            )
        except KeyError as ex:
            raise UpdateFailed("Problems calling Wavin Sentio") from ex

    def get_rooms(self):
        return self.roomdata

    def get_room(self, code):
        for entry in self.roomdata:
            if code == entry["code"]:
                return entry
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

    def get_location(self):
        return self.location
