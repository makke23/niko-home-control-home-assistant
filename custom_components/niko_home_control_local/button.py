"""Buttons for stateless Niko Home Control actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import discover_door_unlock_actions, discover_trigger_buttons
from .entity import NikoDeviceEntity
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
        [
            NikoActionButton(hub, device)
            for device in discover_trigger_buttons(hub.client.devices)
        ]
        + [
            NikoDoorUnlockButton(hub, device)
            for device in discover_door_unlock_actions(hub.client.devices)
        ]
    )


class NikoActionButton(NikoDeviceEntity, ButtonEntity):
    """Execute a stateless Niko action."""

    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_unique_id = f"{device.uuid}_trigger"

    async def async_press(self) -> None:
        await self.hub.async_control_device(
            self.device.uuid, {"BasicState": "Triggered"}
        )


class NikoDoorUnlockButton(NikoDeviceEntity, ButtonEntity):
    """Open a Niko access-control door lock."""

    _attr_icon = "mdi:door-open"

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_unique_id = f"{device.uuid}_door_unlock"
        self._attr_name = f"{device.name} deur openen"

    async def async_press(self) -> None:
        await self.hub.async_control_device(
            self.device.uuid, {"Doorlock": "Open"}
        )
