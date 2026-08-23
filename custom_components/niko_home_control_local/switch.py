"""Switches for Niko Home Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import discover_boost_switches, discover_switches, discover_toggle_actions
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
        [NikoSwitch(hub, device) for device in discover_switches(hub.client.devices)]
        + [
            NikoToggleActionSwitch(hub, device)
            for device in discover_toggle_actions(hub.client.devices)
        ]
        + [NikoBoostSwitch(hub, device) for device in discover_boost_switches(hub.client.devices)]
    )


class NikoSwitch(NikoDeviceEntity, SwitchEntity):
    """A Niko relay action."""

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)

    @property
    def is_on(self) -> bool:
        return str(self.device.properties.get("Status", "Off")).lower() == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Status": "On"})

    async def async_turn_off(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Status": "Off"})


class NikoToggleActionSwitch(NikoDeviceEntity, SwitchEntity):
    """A Niko start/stop or PIR enable/disable action."""

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_unique_id = f"{device.uuid}_basic_state"
        if device.model == "pir":
            self._attr_icon = "mdi:motion-sensor"

    @property
    def is_on(self) -> bool:
        return str(self.device.properties.get("BasicState", "Off")).lower() == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        del kwargs
        if not self.is_on:
            await self._trigger()

    async def async_turn_off(self, **kwargs: Any) -> None:
        del kwargs
        if self.is_on:
            await self._trigger()

    async def _trigger(self) -> None:
        await self.hub.async_control_device(
            self.device.uuid, {"BasicState": "Triggered"}
        )


class NikoBoostSwitch(NikoDeviceEntity, SwitchEntity):
    """Boost mode exposed by a partner device."""

    _attr_icon = "mdi:rocket-launch"

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_unique_id = f"{device.uuid}_boost"
        self._attr_name = f"{device.name} boost"

    @property
    def is_on(self) -> bool:
        return str(self.device.properties.get("Boost", "False")).lower() in {
            "true", "on", "1"
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Boost": "True"})

    async def async_turn_off(self, **kwargs: Any) -> None:
        del kwargs
        await self.hub.async_control_device(self.device.uuid, {"Boost": "False"})
