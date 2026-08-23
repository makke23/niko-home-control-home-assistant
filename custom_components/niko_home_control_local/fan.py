"""Partner ventilation for Niko Home Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import can_control, discover_partner_fans
from .entity import NikoDeviceEntity
from .hub import NikoHub
from .models import NikoDevice

_PRESET_MODES = ["Off", "Low", "Medium", "High", "Automatic"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    async_add_entities(
        NikoPartnerFan(entry.runtime_data, device)
        for device in discover_partner_fans(entry.runtime_data.client.devices)
    )


class NikoPartnerFan(NikoDeviceEntity, FanEntity):
    """A ventilation system coupled through a Niko partner integration."""

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        features = FanEntityFeature(0)
        if can_control(device, "FanSpeed"):
            features |= FanEntityFeature.PRESET_MODE
            self._attr_preset_modes = _PRESET_MODES.copy()
        if can_control(device, "Status"):
            features |= FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        self._attr_supported_features = features

    @property
    def is_on(self) -> bool:
        return str(self.device.properties.get("Status", "On")).lower() == "on"

    @property
    def preset_mode(self) -> str | None:
        value = str(self.device.properties.get("FanSpeed", ""))
        return value if value in _PRESET_MODES else None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in _PRESET_MODES:
            raise ValueError(f"Niet-ondersteunde ventilatiestand: {preset_mode}")
        await self.hub.async_control_device(
            self.device.uuid, {"FanSpeed": preset_mode}
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        del percentage, kwargs
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        await self.hub.async_control_device(self.device.uuid, {"Status": "On"})

    async def async_turn_off(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Status": "Off"})
