"""Lights for Niko Home Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import can_control, discover_lights
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
        NikoLight(entry.runtime_data, device)
        for device in discover_lights(entry.runtime_data.client.devices)
    )


class NikoLight(NikoDeviceEntity, LightEntity):
    """A Niko light or dimmer action."""

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._supports_brightness = can_control(device, "Brightness")
        self._attr_supported_color_modes = {
            ColorMode.BRIGHTNESS if self._supports_brightness else ColorMode.ONOFF
        }
        self._attr_color_mode = next(iter(self._attr_supported_color_modes))

    @property
    def is_on(self) -> bool:
        return str(self.device.properties.get("Status", "Off")).lower() == "on"

    @property
    def brightness(self) -> int | None:
        if not self._supports_brightness:
            return None
        try:
            percentage = float(self.device.properties.get("Brightness", 0))
        except (TypeError, ValueError):
            return None
        return round(max(0.0, min(100.0, percentage)) * 255 / 100)

    async def async_turn_on(self, **kwargs: Any) -> None:
        properties: dict[str, Any] = {"Status": "On"}
        if self._supports_brightness and ATTR_BRIGHTNESS in kwargs:
            properties["Brightness"] = str(round(kwargs[ATTR_BRIGHTNESS] * 100 / 255))
        await self.hub.async_control_device(self.device.uuid, properties)

    async def async_turn_off(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Status": "Off"})
