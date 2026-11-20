"""Select platform for Wavin Sentio integration in Home Assistant."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wavinsentio.wavinsentio import HCMode

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN

OPTION_BY_MODE = {
    HCMode.HC_MODE_HEATING: "heating",
    HCMode.HC_MODE_COOLING: "cooling",
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the heating/cooling mode select if the device supports both modes."""
    dataservice = hass.data[DOMAIN].get("coordinator" + entry.data[CONF_DEVICE_NAME])
    available = dataservice.get_device().lastConfig.sentio.availableHcModes or []
    modes = [mode for mode in OPTION_BY_MODE if mode.value in available]
    # Nothing to choose between on heating-only (or cooling-only) installations.
    if len(modes) > 1:
        async_add_entities([WavinSentioHCModeSelect(dataservice, modes)])


class WavinSentioHCModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for choosing heating or cooling mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "hc_mode"
    _attr_icon = "mdi:thermometer-auto"

    def __init__(self, dataservice: WavinSentioDataCoordinator, modes: list[HCMode]) -> None:
        """Initialize the select with the modes the device supports."""
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._mode_by_option = {OPTION_BY_MODE[mode]: mode for mode in modes}
        self._attr_options = list(self._mode_by_option)

    @property
    def current_option(self) -> str | None:
        """Return the current mode, or None if it is not one of the options."""
        option = OPTION_BY_MODE.get(self._dataservice.get_device().lastConfig.sentio.hcMode)
        return option if option in self._mode_by_option else None

    async def async_select_option(self, option: str) -> None:
        """Change the heating/cooling mode."""
        await self._dataservice.set_hc_mode(self._mode_by_option[option])
        await self.coordinator.async_request_refresh()

    @property
    def unique_id(self) -> str:
        """Return the ID of this entity."""
        return f"{self._dataservice.get_device().name}-HCMode"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._dataservice.get_device().name)},
            name=self._dataservice.get_device().lastConfig.sentio.titlePersonalized,
            manufacturer="Wavin",
            model="Sentio",
        )
