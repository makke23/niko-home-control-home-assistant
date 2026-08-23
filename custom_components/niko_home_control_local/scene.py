"""Scenes for Niko Home Control mood actions."""

from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import discover_scenes
from .entity import NikoDeviceEntity
from .hub import NikoHub
from .models import NikoDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    async_add_entities(
        NikoMoodScene(entry.runtime_data, device)
        for device in discover_scenes(entry.runtime_data.client.devices)
    )


class NikoMoodScene(NikoDeviceEntity, Scene):
    """A Niko mood activated with BasicState=Triggered."""

    _attr_icon = "mdi:palette"

    async def async_activate(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(
            self.device.uuid, {"BasicState": "Triggered"}
        )
