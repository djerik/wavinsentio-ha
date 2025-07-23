"""Switch platform for Wavin Sentio integration in Home Assistant."""

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wavinsentio.wavinsentio import StandbyMode, VacationMode

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up Wavin Sentio switch entities from a config entry."""
    dataservice = hass.data[DOMAIN].get("coordinator"+entry.data[CONF_DEVICE_NAME])
    entities = []
    entities.append(WavinSentioStandbySwitchEntity(dataservice))
    entities.append(WavinSentioVacationSwitchEntity(dataservice))
    async_add_entities(entities)


class WavinSentioStandbySwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch entity for controlling the standby mode of a Wavin Sentio device."""

    def __init__(self, dataservice: WavinSentioDataCoordinator) -> None:
        """Initialize the Wavin Sentio Standby Switch entity."""
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._name = "Standby"
        self._attr_device_class = SwitchDeviceClass.SWITCH

    @property
    def name(self) -> str:
        """Return the display name of this switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if the mode equals standby."""
        return self._dataservice.get_device().lastConfig.sentio.standbyMode == StandbyMode.STANDBY_MODE_ON

    async def async_turn_on(self, **kwargs):
        """Turn on the standby mode."""
        self._dataservice.turn_on_standby()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn off the standby mode."""
        self._dataservice.turn_off_standby()
        await self.coordinator.async_request_refresh()

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return str(self._dataservice.get_device().name ) + "-Standby"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity."""
        return DeviceInfo(
            identifiers= {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._dataservice.get_device().name)
            },
            name = self._dataservice.get_device().lastConfig.sentio.titlePersonalized,
            manufacturer = "Wavin",
            model = "Sentio",
        )

class WavinSentioVacationSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch entity for controlling the vacation mode of a Wavin Sentio device."""

    def __init__(self, dataservice: WavinSentioDataCoordinator) -> None:
        """Initialize the Wavin Sentio Vacation Switch entity."""
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._name = "Vacation"
        self._attr_device_class = SwitchDeviceClass.SWITCH

    @property
    def name(self) -> str:
        """Return the display name of this switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if the mode equals Vacation."""
        return self._dataservice.get_device().lastConfig.sentio.vacationSettings.vacationMode == VacationMode.VACATION_MODE_ON

    async def async_turn_on(self, **kwargs):
        """Turn on the vacation mode."""
        self._dataservice.turn_on_vacation_mode_device()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn off the standby mode."""
        self._dataservice.turn_off_vacation_mode_device()
        await self.coordinator.async_request_refresh()

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return str(self._dataservice.get_device().name ) + "-Vacation"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity."""
        return DeviceInfo(
            identifiers= {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._dataservice.get_device().name)
            },
            name = self._dataservice.get_device().lastConfig.sentio.titlePersonalized,
            manufacturer = "Wavin",
            model = "Sentio",
            serial_number = self._dataservice.get_device().serialNumber,
            sw_version = self._dataservice.get_device().firmwareInstalled,
        )
