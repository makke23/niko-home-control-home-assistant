"""Domestic hot water for Niko partner systems."""

from __future__ import annotations

from homeassistant.components.water_heater import WaterHeaterEntity, WaterHeaterEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import can_control, discover_hot_water_devices
from .entity import NikoDeviceEntity
from .hub import NikoHub
from .models import NikoDevice

_PROGRAMS = ["Home", "Away", "Vacation", "Day", "Night"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    async_add_entities(
        NikoHotWater(entry.runtime_data, device)
        for device in discover_hot_water_devices(entry.runtime_data.client.devices)
    )


class NikoHotWater(NikoDeviceEntity, WaterHeaterEntity):
    """A generic partner domestic-hot-water unit."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5.0
    _attr_max_temp = 80.0
    _attr_operation_list = _PROGRAMS

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        features = WaterHeaterEntityFeature(0)
        if can_control(device, "DomesticHotWaterTemperature"):
            features |= WaterHeaterEntityFeature.TARGET_TEMPERATURE
        if can_control(device, "Program"):
            features |= WaterHeaterEntityFeature.OPERATION_MODE
        self._attr_supported_features = features

    @property
    def current_temperature(self) -> float | None:
        try:
            return float(self.device.properties["DomesticHotWaterTemperature"])
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def target_temperature(self) -> float | None:
        return self.current_temperature

    @property
    def current_operation(self) -> str | None:
        value = str(self.device.properties.get("Program", ""))
        return value if value in _PROGRAMS else None

    async def async_set_temperature(self, **kwargs: float) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self.hub.async_control_device(
                self.device.uuid, {"DomesticHotWaterTemperature": str(temperature)}
            )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode not in _PROGRAMS:
            raise ValueError(f"Niet-ondersteund warmwaterprogramma: {operation_mode}")
        await self.hub.async_control_device(self.device.uuid, {"Program": operation_mode})
