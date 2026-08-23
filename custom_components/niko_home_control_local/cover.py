"""Covers for Niko Home Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import can_control, discover_covers
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
        NikoCover(entry.runtime_data, device)
        for device in discover_covers(entry.runtime_data.client.devices)
    )


class NikoCover(NikoDeviceEntity, CoverEntity):
    """A Niko roll-down shutter, sunblind, gate or venetian blind action."""

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_device_class = {
            "gate": CoverDeviceClass.GATE,
            "reynaers": CoverDeviceClass.WINDOW,
            "rolldownshutter": CoverDeviceClass.SHUTTER,
            "sunblind": CoverDeviceClass.AWNING,
            "velux": CoverDeviceClass.WINDOW,
            "venetianblind": CoverDeviceClass.BLIND,
        }.get(device.model, CoverDeviceClass.SHUTTER)
        features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
        )
        if can_control(device, "Position"):
            features |= CoverEntityFeature.SET_POSITION
        self._attr_supported_features = features

    @property
    def current_cover_position(self) -> int | None:
        try:
            position = int(float(self.device.properties["Position"]))
        except (KeyError, TypeError, ValueError):
            return None
        return max(0, min(100, position))

    @property
    def is_closed(self) -> bool | None:
        position = self.current_cover_position
        return None if position is None else position == 0

    @property
    def is_opening(self) -> bool:
        return self._is_moving_in_direction("Open")

    @property
    def is_closing(self) -> bool:
        return self._is_moving_in_direction("Close")

    def _is_moving_in_direction(self, direction: str) -> bool:
        moving = str(self.device.properties.get("Moving", "False")).lower()
        last_direction = str(self.device.properties.get("LastDirection", ""))
        return moving in {"1", "on", "true", "yes"} and last_direction == direction

    async def async_open_cover(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Action": "Open"})

    async def async_close_cover(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Action": "Close"})

    async def async_stop_cover(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Action": "Stop"})

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = max(0, min(100, int(kwargs[ATTR_POSITION])))
        await self.hub.async_control_device(
            self.device.uuid, {"Position": str(position)}
        )
