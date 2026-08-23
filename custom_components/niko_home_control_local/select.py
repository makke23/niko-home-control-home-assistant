"""Select entities for Niko Home Control."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import discover_charging_mode_devices, discover_fan_speed_actions
from .entity import NikoDeviceEntity
from .hub import NikoHub
from .models import NikoDevice

FAN_SPEED_OPTIONS = ["Low", "Medium", "High", "Boost"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    hub = entry.runtime_data
    async_add_entities(
        [
            NikoFanSpeedSelect(hub, device)
            for device in discover_fan_speed_actions(hub.client.devices)
        ]
        + [
            NikoChargingModeSelect(hub, device)
            for device in discover_charging_mode_devices(hub.client.devices)
        ]
    )


class NikoFanSpeedSelect(NikoDeviceEntity, SelectEntity):
    """Select the speed of a Niko fan action."""

    _attr_icon = "mdi:fan"
    _attr_options = FAN_SPEED_OPTIONS

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_unique_id = f"{device.uuid}_fan_speed"
        self._attr_name = f"{device.name} speed"

    @property
    def current_option(self) -> str | None:
        value = str(self.device.properties.get("FanSpeed", ""))
        return value if value in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise ValueError(f"Unsupported Niko fan speed: {option}")
        await self.hub.async_control_device(
            self.device.uuid, {"FanSpeed": option}
        )


class NikoChargingModeSelect(NikoDeviceEntity, SelectEntity):
    """Select Solar, Normal or Smart EV charging."""

    _attr_icon = "mdi:ev-station"
    _attr_options = ["Solar", "Normal", "Smart"]

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_unique_id = f"{device.uuid}_charging_mode"
        self._attr_name = f"{device.name} charging mode"

    @property
    def current_option(self) -> str | None:
        value = str(self.device.properties.get("Chargingmode", ""))
        return value if value in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise ValueError(f"Unsupported charging mode: {option}")
        await self.hub.async_control_device(
            self.device.uuid, {"Chargingmode": option}
        )
