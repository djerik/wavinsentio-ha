"""Wavin Sentio sensor platform: room temperature/humidity/floor temperature and outdoor temperature."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
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

    await _async_migrate_outdoor_ids(hass, entry, dataservice.device_name)

    entities = [WavinSentioRoomSensor(dataservice, room, measurement)
                for room in dataservice.get_rooms()
                for measurement in ROOM_MEASUREMENTS
                if has_measurement(room, measurement)]

    entities.extend(WavinSentioOutdoorTemperatureSensor(dataservice, outdoorTemperatureSensor)
                    for outdoorTemperatureSensor in dataservice.get_device().lastConfig.sentio.outdoorTemperatureSensors)

    async_add_entities(entities)


async def _async_migrate_outdoor_ids(hass: HomeAssistant, entry, device_name: str) -> None:
    """Scope outdoor sensor IDs with the controller name.

    The sensor ID alone is not unique across controllers, so a second controller
    on the same account had its outdoor temperature entity rejected.
    """
    old_prefix = "OutdoorTemperature-"

    @callback
    def _new_unique_id(entity_entry: er.RegistryEntry) -> dict | None:
        if entity_entry.domain == "sensor" and entity_entry.unique_id.startswith(old_prefix):
            return {"new_unique_id": f"{device_name}-{entity_entry.unique_id}"}
        return None

    await er.async_migrate_entries(hass, entry.entry_id, _new_unique_id)

    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        new_identifiers = {
            (domain, f"{device_name}-{identifier}")
            if domain == DOMAIN and identifier.startswith(old_prefix)
            else (domain, identifier)
            for domain, identifier in device.identifiers
        }
        if new_identifiers != device.identifiers:
            device_registry.async_update_device(device.id, new_identifiers=new_identifiers)


class WavinSentioRoomSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Wavin Sentio room sensor (temperature or humidity)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

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

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

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
    def native_value(self):
        """Return the state of the sensor."""
        for outdoorTemperatureSensor in self._dataservice.get_device().lastConfig.sentio.outdoorTemperatureSensors:
            if outdoorTemperatureSensor.id == self._outdoorTemperatureSensor.id:
                self._state = outdoorTemperatureSensor.outdoorTemperature
        return self._state

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return f"{self._dataservice.device_name}-OutdoorTemperature-{self._outdoorTemperatureSensor.id}"

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
