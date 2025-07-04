"""Climate platform for Wavin Sentio integration."""

from typing import cast

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wavinsentio.wavinsentio import Room

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN

PRESET_MODES = {
    "Eco": {"profile": "eco"},
    "Comfort": {"profile": "comfort"},
    "Extracomfort": {"profile": "extra"},
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up Wavin Sentio climate entities from a config entry."""
    dataservice = cast(WavinSentioDataCoordinator,hass.data[DOMAIN].get("coordinator" + entry.data[CONF_DEVICE_NAME]))

    rooms = dataservice.get_device().lastConfig.sentio.rooms

    entities = []
    for room in rooms:
        ws = WavinSentioClimateEntity(hass, room, dataservice)
        entities.append(ws)
    async_add_entities(entities)

class WavinSentioClimateEntity(CoordinatorEntity, ClimateEntity):
    """Representation of a Wavin Sentio Climate device."""

    def __init__(self, hass: HomeAssistant, room: Room, dataservice: WavinSentioDataCoordinator) -> None:
        """Initialize the climate device."""
        super().__init__(dataservice)
        self._name = room.titlePersonalized
        self._room_id = room.id
        self._hvac_modes = [HVACMode.HEAT]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        self._preset_mode = None
        self._operation_list = None
        self._unit_of_measurement = UnitOfTemperature.CELSIUS
        self._away = False
        self._on = True
        self._current_operation_mode = None
        self._dataservice = dataservice

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            return temp_room.airTemperature
        return None

    @property
    def current_humidity(self):
        """Return the current humidity."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            return temp_room.humidity
        return None


    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            return temp_room.setpointTemperature
        return None

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            return temp_room.minSetpointTemperature
        return None

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            return temp_room.maxSetpointTemperature
        return None

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            return "Eco"
        #TODO: Support other modes
            #if temp_room["tempDesired"] == temp_room["tempEco"]:
                #return "Eco"
            #if temp_room["tempDesired"] == temp_room["tempComfort"]:
                #return "Comfort"
            #if temp_room["tempDesired"] == temp_room["tempExtra"]:
                #return "Extracomfort"
        return self._preset_mode

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return list(PRESET_MODES)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        self._dataservice.set_new_profile(
            self._room_id, PRESET_MODES[preset_mode]["profile"]
        )
        await self.coordinator.async_request_refresh()

    @property
    def is_away_mode_on(self):
        """Return if away mode is on."""
        return self._away

    @property
    def is_on(self):
        """Return true if the device is on."""
        return self._on

    @property
    def current_operation(self):
        """Return current operation ie. manual, auto, frost."""
        return self._current_operation_mode

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            await self._dataservice.set_new_temperature(
                self._room_id, kwargs.get(ATTR_TEMPERATURE)
            )
            await self.coordinator.async_request_refresh()

    def turn_away_mode_on(self):
        """Turn away mode on."""
        self._away = True
        # self._device.set_location_to_frost()

    def turn_away_mode_off(self):
        """Turn away mode off."""
        self._away = False
        # self._device.set_temperature_to_manual()

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room.temperatureState == "TEMPERATURE_STATE_HEATING":
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return HVACMode.HEAT

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return self._room_id

    @property
    def device_info(self):
        """Return device information for this climate entity."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            return {
                "identifiers": {
                    # Serial numbers are unique identifiers within a specific domain
                    (DOMAIN, self.unique_id)
                },
                "name": self._name,
                "manufacturer": "Wavin",
                "model": "Sentio",
            }
        return {}

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        # Extract air and floor temp and store in extended attributes.
        # Overrides any super extra_state_attributes
        attrs = {}
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room is not None:
            attrs["current_temperature_floor"] = temp_room.floorTemperature
            attrs["current_temperature_air"] = temp_room.airTemperature
            #TODO: Add support for low battery
            #if "peripheryBatteryLow" in temp_room["warnings"]:
                #attrs["low_battery"] = True
            #else:
                #attrs["low_battery"] = False

        return attrs
