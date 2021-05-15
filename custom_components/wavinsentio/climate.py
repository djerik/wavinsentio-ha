from datetime import timedelta
import logging
import re
from typing import Any, Callable, Dict, Optional
from requests.exceptions import ConnectTimeout, HTTPError

from homeassistant import config_entries, core
from homeassistant.core import callback
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_TEMPERATURE,
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
    PRECISION_WHOLE,
    PRECISION_TENTHS,
)

from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_IDLE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.exceptions import ConfigEntryNotReady

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
import voluptuous as vol

from .const import DOMAIN, CONF_LOCATION_ID

from wavinsentio.wavinsentio import WavinSentio

PRESET_MODES = {
    "Eco": {"profile": "eco"},
    "Comfort": {"profile": "comfort"},
    "Extracomfort": {"profile": "extra"},
}

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

_LOGGER = logging.getLogger(__name__)

UPDATE_DELAY = timedelta(seconds=120)


async def async_setup_entry(hass, entry, async_add_entities):
    api = await hass.async_add_executor_job(
        WavinSentio, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    rooms = await hass.async_add_executor_job(
        api.get_rooms, entry.data[CONF_LOCATION_ID]
    )

    dataservice = WavinSentioDataService(hass, api, entry.data[CONF_LOCATION_ID], rooms)
    dataservice.async_setup()
    await dataservice.coordinator.async_refresh()

    entities = []
    for room in rooms:
        ws = WavinSentioEntity(hass, room, dataservice)
        entities.append(ws)
    async_add_entities(entities)


class WavinSentioDataService:
    """Get and update the latest data."""

    def __init__(self, hass, api, location_id, roomdata):
        """Initialize the data object."""
        self.api = api
        self.location_id = location_id

        self.roomdata = roomdata

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
            self.roomdata = await self.hass.async_add_executor_job(
                self.api.get_rooms, self.location_id
            )
        except KeyError as ex:
            raise UpdateFailed("Missing overview data, skipping update") from ex

    def get_room(self, code):
        for entry in self.roomdata:
            if code == entry["code"]:
                return entry
        return None

    def set_new_temperature(self, code, temperature):
        _LOGGER.debug("Setting temperature: %s", temperature)
        self.hass.async_add_executor_job(self.api.set_temperature, code, temperature)

    def set_new_profile(self, code, profile):
        _LOGGER.debug("Setting profile: %s", profile)
        self.hass.async_add_executor_job(self.api.set_profile, code, profile)


class WavinSentioEntity(CoordinatorEntity, ClimateEntity):
    """Representation of a Wavin Sentio device."""

    # mode_map = {"prog": STATE_AUTO, "fixed": STATE_MANUAL}

    def __init__(self, hass, room, dataservice):
        super().__init__(dataservice.coordinator)
        """Initialize the climate device."""
        _LOGGER.info("Setting up Wavin Sentio component")
        self._name = room["name"]
        self._roomcode = room["code"]
        self._hvac_mode = (
            HVAC_MODE_HEAT if room["status"] == "heating" else HVAC_MODE_OFF
        )
        self._hvac_modes = [HVAC_MODE_HEAT]
        self._support_flags = SUPPORT_FLAGS
        self._preset_mode = None
        self._operation_list = None  # = [STATE_AUTO, STATE_MANUAL]
        self._unit_of_measurement = TEMP_CELSIUS
        self._away = False
        self._on = True
        self._current_operation_mode = None  # = STATE_MANUAL
        self._dataservice = dataservice

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

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
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room is not None:
            return self._dataservice.get_room(self._roomcode)["tempCurrent"]

    @property
    def current_humidity(self):
        """Return the current humidity."""
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room is not None:
            return temp_room["humidityCurrent"]

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room is not None:
            return temp_room["tempDesired"]

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room is not None:
            return temp_room["tempSpan"]["minimum"]

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room is not None:
            return temp_room["tempSpan"]["maximum"]

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room is not None:
            if temp_room["tempDesired"] == temp_room["tempEco"]:
                return "Eco"
            if temp_room["tempDesired"] == temp_room["tempComfort"]:
                return "Comfort"
            if temp_room["tempDesired"] == temp_room["tempExtra"]:
                return "Extracomfort"
        return self._preset_mode

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return list(PRESET_MODES)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        self._dataservice.set_new_profile(
            self._roomcode, PRESET_MODES[preset_mode]["profile"]
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
            self._dataservice.set_new_temperature(
                self._roomcode, kwargs.get(ATTR_TEMPERATURE)
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

    def set_operation_mode(self, operation_mode):
        """
        Set new target operation mode.
        Switch device on if was previously off
        """
        if not self.is_on:
            self._on = True
        # if operation_mode == STATE_AUTO:
        # self._device.set_temperature_to_auto()
        #   self._current_operation_mode = operation_mode
        #  return
        # if operation_mode == STATE_MANUAL:
        # self._device.set_temperature_to_manual()
        #   self._current_operation_mode = operation_mode

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported"""
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room["status"] == "heating":
            return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_IDLE

    @property
    def hvac_mode(self):
        temp_room = self._dataservice.get_room(self._roomcode)
        self._hvac_mode = (
            HVAC_MODE_HEAT if temp_room["status"] == "heating" else HVAC_MODE_OFF
        )
        # Return current operation mode ie. heat, cool, idle.
        return self._hvac_mode

    @property
    def hvac_modes(self):
        # Return the list of available operation modes.
        return self._hvac_modes

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return self._roomcode

    @property
    def device_info(self):
        temp_room = self._dataservice.get_room(self._roomcode)
        if temp_room is not None:
            return {
                "identifiers": {
                    # Serial numbers are unique identifiers within a specific domain
                    (DOMAIN, self.unique_id)
                },
                "name": self._name,
                "manufacturer": "Wavin",
                "model": "Sentio"
                # "sw_version": self.light.swversion,
                # "via_device": (hue.DOMAIN, self.api.bridgeid),
            }
        return
