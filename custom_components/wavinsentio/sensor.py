"""Wavin Sentio Outdoor Temperature Sensor integration for Home Assistant."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wavinsentio.wavinsentio import OutdoorTemperatureSensor

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the Wavin Sentio outdoor temperature sensor entity.

    Args:
        hass: Home Assistant instance.
        entry: Config entry for the integration.
        async_add_entities: Function to add entities asynchronously.

    """
    dataservice = hass.data[DOMAIN].get("coordinator"+entry.data[CONF_DEVICE_NAME])


    if not dataservice or not dataservice.get_device().lastConfig.sentio.outdoorTemperatureSensors:
        return

    entities = [(WavinSentioOutdoorTemperatureSensor(dataservice,outdoorTemperatureSensor))
                for outdoorTemperatureSensor in dataservice.get_device().lastConfig.sentio.outdoorTemperatureSensors]

    async_add_entities(entities)


class WavinSentioOutdoorTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Outdoor Temperature Sensor."""

    def __init__(self, dataservice : WavinSentioDataCoordinator, outdoorTemperatureSensor: OutdoorTemperatureSensor) -> None:
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._state = None
        self._dataservice = dataservice
        self._outdoorTemperatureSensor = outdoorTemperatureSensor

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Outdoor Temperature"

    @property
    def state(self):
        """Return the state of the sensor."""
        for outdoorTemperatureSensor in self._dataservice.get_device().lastConfig.sentio.outdoorTemperatureSensors:
            if outdoorTemperatureSensor.id == self._outdoorTemperatureSensor.id:
                self._state = outdoorTemperatureSensor.outdoorTemperature
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.TEMPERATURE

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return f"OutdoorTemperature-{self._outdoorTemperatureSensor.id}"

    @property
    def device_info(self):
        """Return device information for Home Assistant device registry."""
        return {
            "identifiers": {
                (DOMAIN, self.unique_id)
            },
            "name": self.name,
            "manufacturer": "Wavin",
            "model": "Sentio",
        }
