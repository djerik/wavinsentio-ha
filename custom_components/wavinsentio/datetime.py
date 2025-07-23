"""Wavin Sentio Vacation Mode Until datetime entity.

This module defines the entity for managing the 'Vacation Mode Until' datetime
setting for Wavin Sentio devices in Home Assistant.
"""

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Wavin Sentio Vacation Until datetime entity.

    Args:
        hass: Home Assistant instance.
        config_entry: Configuration entry for the integration.
        async_add_entities: Function to add entities asynchronously.

    """
    dataservice = hass.data[DOMAIN].get("coordinator"+config_entry.data[CONF_DEVICE_NAME])
    async_add_entities([WavinSentioVacationUntilEntity(dataservice)])

class WavinSentioVacationUntilEntity(CoordinatorEntity, DateTimeEntity):
    """Entity representing the 'Vacation Mode Until' datetime for a Wavin Sentio device.

    Attributes
    ----------
    _dataservice : WavinSentioDataCoordinator
        The coordinator providing device data and services.
    _attr_name : str
        The name of the entity.
    _attr_unique_id : str
        Unique identifier for the entity.

    """

    def __init__(self, dataservice: WavinSentioDataCoordinator) -> None:
        """Initialize the Wavin Sentio Vacation Until entity."""
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._attr_name = "Vacation Mode Until"
        self._attr_unique_id = f"{dataservice.get_device().name}_vacation_mode_until"

    @property
    def native_value(self):
        """Return the current 'Vacation Mode Until' datetime value for the device."""
        return self._dataservice.get_device().lastConfig.sentio.vacationSettings.vacationModeUntil

    async def async_set_value(self, value):
        """Set the vacation mode until value.

        Args:
            value: The new datetime value to set for vacation mode.

        """
        await self._dataservice.set_vacation_mode_until(value)
        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity."""
        return DeviceInfo(
            identifiers= {
                (DOMAIN, self._dataservice.get_device().name)
            },
            name = self._dataservice.get_device().lastConfig.sentio.titlePersonalized,
            manufacturer = "Wavin",
            model = "Sentio",
            serial_number = self._dataservice.get_device().serialNumber,
            sw_version = self._dataservice.get_device().firmwareInstalled,
        )
