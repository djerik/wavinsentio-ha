"""Wavin Sentio sensor platform: room temperature/humidity/floor temperature and outdoor temperature."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wavinsentio.wavinsentio import OutdoorTemperatureSensor, Room

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN

ROOM_MEASUREMENTS = ["airTemperature", "humidity", "floorTemperature"]

MEASUREMENT_NAMES = {
    "airTemperature": "Temperature",
    "humidity": "Humidity",
    "floorTemperature": "Floor Temperature",
}


def has_measurement(room: Room, measurement: str) -> bool:
    """Return True if the room reports a value for the measurement.

    The wavinsentio library defaults missing values to 0, so rooms without
    the corresponding sensor (e.g. no humidity-capable thermostat) report 0.
    """
    return getattr(room, measurement, None) not in (None, 0)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the Wavin Sentio sensor entities.

    Args:
        hass: Home Assistant instance.
        entry: Config entry for the integration.
        async_add_entities: Function to add entities asynchronously.

    """
    dataservice = hass.data[DOMAIN].get("coordinator"+entry.data[CONF_DEVICE_NAME])

    if not dataservice:
        return

    entities = [WavinSentioRoomSensor(dataservice, room, measurement)
                for room in dataservice.get_rooms()
                for measurement in ROOM_MEASUREMENTS
                if has_measurement(room, measurement)]

    entities.extend(WavinSentioOutdoorTemperatureSensor(dataservice, outdoorTemperatureSensor)
                    for outdoorTemperatureSensor in dataservice.get_device().lastConfig.sentio.outdoorTemperatureSensors)

    async_add_entities(entities)


class WavinSentioRoomSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Wavin Sentio room sensor (temperature or humidity)."""

    def __init__(self, dataservice: WavinSentioDataCoordinator, room: Room, measurement: str) -> None:
        """Initialize the sensor."""
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._room_id = room.id
        self._room_name = room.titlePersonalized
        self._measurement = measurement
        if measurement == "humidity":
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
        else:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_suggested_display_precision = 1

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._room_name} {MEASUREMENT_NAMES[self._measurement]}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        room = self._dataservice.get_room(self._room_id)
        if room is None:
            return None
        return getattr(room, self._measurement)

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return f"{self._dataservice.device_name}-{self._room_id}-{self._measurement}"

    @property
    def device_info(self):
        """Return device information for Home Assistant device registry."""
        return {
            "identifiers": {
                (DOMAIN, self._room_id)
            },
            "name": self._room_name,
            "manufacturer": "Wavin",
            "model": "Sentio",
        }


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
