from datetime import timedelta
import logging

from homeassistant.core import callback
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from homeassistant.const import TEMP_CELSIUS

from homeassistant.exceptions import ConfigEntryAuthFailed

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, CONF_LOCATION_ID

from wavinsentio.wavinsentio import WavinSentio, UnauthorizedException

_LOGGER = logging.getLogger(__name__)

UPDATE_DELAY = timedelta(seconds=120)


async def async_setup_entry(hass, entry, async_add_entities):
    try:
        api = await hass.async_add_executor_job(
            WavinSentio, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )
    except UnauthorizedException as err:
        raise ConfigEntryAuthFailed(err) from err

    location = await hass.async_add_executor_job(
        api.get_location, entry.data[CONF_LOCATION_ID]
    )

    dataservice = WavinSentioSensorDataService(
        hass, api, entry.data[CONF_LOCATION_ID], location
    )
    dataservice.async_setup()

    await dataservice.coordinator.async_refresh()

    outdoorTemperatureSensor = WavinSentioOutdoorTemperatureSensor(dataservice)

    entities = []
    entities.append(outdoorTemperatureSensor)

    async_add_entities(entities)


class WavinSentioSensorDataService:
    """Get and update the latest data."""

    def __init__(self, hass, api, location_id, location):
        """Initialize the data object."""
        self.api = api
        self.location_id = location_id

        self.location = location

        self.hass = hass
        self.coordinator = None

    @callback
    def async_setup(self):
        """Coordinator creation."""
        self.coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name="WavinSentioDataService",
            update_method=self.async_update_data,
            update_interval=self.update_interval,
        )

    @property
    def update_interval(self):
        return UPDATE_DELAY

    async def async_update_data(self):
        try:
            self.location = await self.hass.async_add_executor_job(
                self.api.get_location, self.location_id
            )
        except KeyError as ex:
            raise UpdateFailed("Missing overview data, skipping update") from ex

    def get_location(self):
        return self.location


class WavinSentioOutdoorTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Outdoor Temperature Sensor."""

    def __init__(self, dataservice):
        """Initialize the sensor."""
        super().__init__(dataservice.coordinator)
        self._state = None
        self._dataservice = dataservice

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._dataservice.get_location()["name"]

    @property
    def state(self):
        """Return the state of the sensor."""
        self._state = self._dataservice.get_location()["attributes"]["outdoor"][
            "temperature"
        ]
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def device_class(self):
        return "temperature"

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return self._dataservice.get_location()["serialNumber"]

    @property
    def device_info(self):
        temp_location = self._dataservice.get_location()
        if temp_location is not None:
            return {
                "identifiers": {
                    # Serial numbers are unique identifiers within a specific domain
                    (DOMAIN, self.unique_id)
                },
                "name": self.name,
                "manufacturer": "Wavin",
                "model": "Sentio",
            }
        return
