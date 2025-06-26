from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity

from homeassistant.const import UnitOfTemperature

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)

UPDATE_DELAY = timedelta(seconds=120)


async def async_setup_entry(hass, entry, async_add_entities):
    dataservice = hass.data[DOMAIN].get("coordinator"+entry.data[CONF_DEVICE_NAME])

    outdoor_temperature_sensor = WavinSentioOutdoorTemperatureSensor(dataservice)

    entities = []
    entities.append(outdoor_temperature_sensor)

    async_add_entities(entities)


class WavinSentioOutdoorTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Outdoor Temperature Sensor."""

    def __init__(self, dataservice):
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Outdoor Temperature"

    @property
    def state(self):
        """Return the state of the sensor."""
        self._state = self._dataservice.get_device().outdoorTemperature
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def device_class(self):
        return "temperature"

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return self._dataservice.get_device().serialNumber + "-OutdoorTemperature"

    @property
    def device_info(self):
        temp_device = self._dataservice.get_device()
        if temp_device is not None:
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
