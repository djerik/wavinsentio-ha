from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wavinsentio.wavinsentio import HCMode

from .const import CONF_DEVICE_NAME, DOMAIN

OPTION_HEATING = "Heating"
OPTION_COOLING = "Cooling"


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    dataservice = hass.data[DOMAIN].get("coordinator" + entry.data[CONF_DEVICE_NAME])
    async_add_entities([WavinSentioHCModeSelect(dataservice)])


class WavinSentioHCModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for choosing heating or cooling mode."""

    _attr_options = [OPTION_HEATING, OPTION_COOLING]
    _attr_icon = "mdi:thermometer-auto"

    def __init__(self, dataservice) -> None:
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._attr_name = "Heating/Cooling mode"

    @property
    def current_option(self) -> str | None:
        mode = self._dataservice.get_device().lastConfig.sentio.hcMode
        if mode == HCMode.HC_MODE_COOLING:
            return OPTION_COOLING
        if mode == HCMode.HC_MODE_HEATING:
            return OPTION_HEATING
        return None

    async def async_select_option(self, option: str) -> None:
        if option == OPTION_COOLING:
            await self.hass.async_add_executor_job(self._dataservice.turn_on_cooling_mode)
        else:
            await self.hass.async_add_executor_job(self._dataservice.turn_on_heating_mode)
        await self.coordinator.async_request_refresh()

    @property
    def unique_id(self) -> str:
        return f"{self._dataservice.get_device().name}-HCMode"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._dataservice.get_device().name)},
            name=self._dataservice.get_device().lastConfig.sentio.titlePersonalized,
            manufacturer="Wavin",
            model="Sentio",
        )