from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from .const import DOMAIN, CONF_LOCATION_ID


async def async_setup_entry(hass, entry, async_add_entities):
    dataservice = hass.data[DOMAIN].get("coordinator"+entry.data[CONF_LOCATION_ID])
    entities = []
    entities.append(WavinSentioStandbySwitchEntity(dataservice))
    async_add_entities(entities)


class WavinSentioStandbySwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, dataservice):
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
        """Return true if the mode equals standby"""
        return self._dataservice.get_location()["attributes"]["mode"] == "standby"

    async def async_turn_on(self, **kwargs):
        self._dataservice.turn_on_standby()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        self._dataservice.turn_off_standby()
        await self.coordinator.async_request_refresh()

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return str(self._dataservice.get_location()["serialNumber"]) + "-Standby"

    @property
    def device_info(self):
        temp_location = self._dataservice.get_location()
        if temp_location is not None:
            return {
                "identifiers": {
                    # Serial numbers are unique identifiers within a specific domain
                    (DOMAIN, self.unique_id)
                },
                "name": "Standby",
                "manufacturer": "Wavin",
                "model": "Sentio",
            }
        return
