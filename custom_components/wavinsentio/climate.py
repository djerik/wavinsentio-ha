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
from wavinsentio.wavinsentio import HCMode, Room, StandbyMode, VacationMode

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN

PRESET_MODES = {
    "Eco": {"type": "TYPE_ECO"},
    "Comfort": {"type": "TYPE_COMFORT"},
    "Extracomfort": {"type": "TYPE_EXTRA_COMFORT"},
    "Vacation": {"type": "TYPE_VACATION"},
}

HVAC_MODES = {
    "HC_MODE_HEATING": HVACMode.HEAT,
    "HC_MODE_COOLING": HVACMode.COOL,
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
        availableHcModes = dataservice.get_device().lastConfig.sentio.availableHcModes
        _hvac_modes = []
        for mode in availableHcModes:
            if mode == HCMode.HC_MODE_HEATING.value:
                _hvac_modes.append(HVACMode.HEAT)
            elif mode == HCMode.HC_MODE_COOLING.value:
                _hvac_modes.append(HVACMode.COOL)
        self._hvac_modes = _hvac_modes
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        self._preset_mode = None
        self._unit_of_measurement = UnitOfTemperature.CELSIUS
        self._on = True
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
        if temp_room.vacationMode == VacationMode.VACATION_MODE_ON:
            return "Vacation"
        for preset in temp_room.temperaturePresets :
            if preset.setpointTemperature == temp_room.setpointTemperature:
                for mode, details in PRESET_MODES.items():
                    if details.get("type") == preset.type:
                        return mode
        return None

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return list(PRESET_MODES)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        if preset_mode not in PRESET_MODES:
            raise ValueError(f"Invalid preset mode: {preset_mode}")
        if self._dataservice.get_device().lastConfig.sentio.standbyMode == StandbyMode.STANDBY_MODE_ON:
            raise ValueError("Device is in standby mode, cannot set preset.")
        if preset_mode == "Vacation" and self._dataservice.get_device().lastConfig.sentio.vacationSettings.vacationMode != VacationMode.VACATION_MODE_ON:
            raise ValueError("Device is not in vacation mode, cannot set preset.")
        if preset_mode == "Vacation":
            self._dataservice.turn_on_vacation_mode_room(
                self._room_id
            )
        else:
            if self._dataservice.get_device().lastConfig.sentio.vacationSettings.vacationMode == VacationMode.VACATION_MODE_ON:
                self._dataservice.turn_off_vacation_mode_room(
                    self._room_id
                )
            temp_room = self._dataservice.get_room(self._room_id)
            for mode, details in PRESET_MODES.items():
                if mode == preset_mode:
                    for preset in temp_room.temperaturePresets:
                        if preset.type == details.get("type") and preset.hcMode == self._dataservice.get_device().lastConfig.sentio.hcMode.value:
                            self._dataservice.set_new_temperature(
                                self._room_id, preset.setpointTemperature
                            )
                            break
                    break
        await self.coordinator.async_request_refresh()

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
        if self._dataservice.get_device().lastConfig.sentio.vacationSettings.vacationMode == VacationMode.VACATION_MODE_ON:
            raise ValueError("Device is in vacation mode, cannot set temperature.")
        if self._dataservice.get_device().lastConfig.sentio.standbyMode == StandbyMode.STANDBY_MODE_ON:
            raise ValueError("Device is in standby mode, cannot set temperature.")
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            await self._dataservice.set_new_temperature(
                self._room_id, kwargs.get(ATTR_TEMPERATURE)
            )
            await self.coordinator.async_request_refresh()

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        temp_room = self._dataservice.get_room(self._room_id)
        if temp_room.temperatureState == "TEMPERATURE_STATE_HEATING":
            return HVACAction.HEATING
        if temp_room.temperatureState == "TEMPERATURE_STATE_COOLING":
            return HVACAction.COOLING
        return HVACAction.IDLE

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        if( self._dataservice.get_device().lastConfig.sentio.hcMode == HCMode.HC_MODE_HEATING):
            return HVACMode.HEAT
        if( self._dataservice.get_device().lastConfig.sentio.hcMode == HCMode.HC_MODE_COOLING):
            return HVACMode.COOL
        raise ValueError("Unknown HVAC mode")

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        raise ValueError("You cannot set the HVAC mode directly.")

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
        return attrs
