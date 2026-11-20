"""Binary sensor platform for Wavin Sentio room notifications."""

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wavinsentio.wavinsentio import Room

from . import WavinSentioDataCoordinator
from .const import CONF_DEVICE_NAME, DOMAIN


@dataclass(frozen=True, kw_only=True)
class WavinSentioNotificationDescription(BinarySensorEntityDescription):
    """Describes a binary sensor that is on while a room reports a notification."""

    notification_key: str


NOTIFICATIONS = (
    WavinSentioNotificationDescription(
        key="low_battery",
        notification_key="KEY_ROOM_PERIPHERAL_LOW_BATTERY",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinSentioNotificationDescription(
        key="peripheral_lost",
        translation_key="peripheral_lost",
        notification_key="KEY_ROOM_PERIPHERAL_LOST",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WavinSentioNotificationDescription(
        key="frost_protection",
        translation_key="frost_protection",
        notification_key="KEY_ROOM_FROST_PROTECTION_ACTIVE",
        icon="mdi:snowflake-alert",
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the notification binary sensors for every room."""
    dataservice = hass.data[DOMAIN].get("coordinator" + entry.data[CONF_DEVICE_NAME])
    async_add_entities(
        WavinSentioRoomNotificationSensor(dataservice, room, description)
        for room in dataservice.get_rooms()
        for description in NOTIFICATIONS
    )


class WavinSentioRoomNotificationSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on while the room reports the notification."""

    entity_description: WavinSentioNotificationDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        dataservice: WavinSentioDataCoordinator,
        room: Room,
        description: WavinSentioNotificationDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(dataservice)
        self.entity_description = description
        self._dataservice = dataservice
        self._room_id = room.id
        self._room_name = room.titlePersonalized
        self._attr_unique_id = f"{dataservice.device_name}-{room.id}-{description.key}"

    def _notification(self):
        """Return the matching notification of the room, or None."""
        room = self._dataservice.get_room(self._room_id)
        if room is None:
            return None
        for notification in room.notifications:
            if notification.key == self.entity_description.notification_key:
                return notification
        return None

    @property
    def is_on(self) -> bool:
        """Return true while the room reports the notification."""
        return self._notification() is not None

    @property
    def extra_state_attributes(self):
        """Return when the notification was raised."""
        notification = self._notification()
        if notification is None:
            return {}
        return {"since": notification.timestamp}

    @property
    def device_info(self):
        """Return device information, shared with the room's other entities."""
        return {
            "identifiers": {(DOMAIN, self._room_id)},
            "name": self._room_name,
            "manufacturer": "Wavin",
            "model": "Sentio",
        }
