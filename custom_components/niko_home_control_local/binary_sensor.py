"""Binary sensors for Niko Home Control."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import NikoBinaryDescription, discover_binary_statuses
from .entity import NikoControllerEntity, NikoDeviceEntity
from .hub import NikoHub
from .models import NikoDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    hub = entry.runtime_data
    async_add_entities(
        [NikoConnectionBinarySensor(hub)]
        + [
            NikoActionBinarySensor(hub, device, description)
            for device, description in discover_binary_statuses(hub.client.devices)
        ]
    )


class NikoConnectionBinarySensor(NikoControllerEntity, BinarySensorEntity):
    """Show whether Home Assistant is connected to the Niko controller."""

    _attr_translation_key = "connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub: NikoHub) -> None:
        super().__init__(hub, "connected")

    @property
    def is_on(self) -> bool:
        return self.hub.connected

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        if not self.hub.last_error:
            return None
        return {"last_error": self.hub.last_error}


class NikoActionBinarySensor(NikoDeviceEntity, BinarySensorEntity):
    """Boolean state reported by a Niko action."""

    def __init__(
        self,
        hub: NikoHub,
        device: NikoDevice,
        description: NikoBinaryDescription,
    ) -> None:
        super().__init__(hub, device)
        self.description = description
        self._attr_unique_id = f"{device.uuid}_{description.property_name}"
        self._attr_name = f"{device.name} {description.name}"
        if description.device_class is not None:
            self._attr_device_class = BinarySensorDeviceClass(description.device_class)
        if description.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        value = self.device.properties.get(self.description.property_name, False)
        return str(value).strip().lower() in self.description.on_values
