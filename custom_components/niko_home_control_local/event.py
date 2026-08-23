"""Notification events for Niko Home Control."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import NikoControllerEntity
from .hub import NikoHub
from .models import NikoNotification


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    async_add_entities([NikoNotificationEvent(entry.runtime_data)])


class NikoNotificationEvent(NikoControllerEntity, EventEntity):
    """Expose newly raised Niko notifications to Home Assistant."""

    _attr_event_types = ["alarm", "notification"]
    _attr_icon = "mdi:message-alert"
    _attr_translation_key = "notification"

    def __init__(self, hub: NikoHub) -> None:
        super().__init__(hub, "notification")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.hub.client.add_notification_listener(self._handle_notification)
        )

    @callback
    def _handle_notification(self, notification: NikoNotification) -> None:
        self._trigger_event(
            notification.notification_type,
            {
                "text": notification.text,
                "time_occurred": notification.time_occurred,
                "notification_id": notification.uuid,
                "status": notification.status,
            },
        )
        self.async_write_ha_state()
