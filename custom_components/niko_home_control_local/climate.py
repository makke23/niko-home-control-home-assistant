"""Climate entities for Niko Home Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import can_control, discover_climate_devices
from .entity import NikoDeviceEntity
from .hub import NikoHub
from .models import NikoDevice

_STANDARD_PROGRAMS = ["Day", "Night", "Eco", "Off", "Prog1", "Prog2", "Prog3"]
_HVAC_PROGRAMS = ["Day", "Night", "Custom", "Prog1", "Prog2"]
_FAN_SPEEDS = ["Low", "Medium", "High"]


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    async_add_entities(
        NikoClimate(entry.runtime_data, device)
        for device in discover_climate_devices(entry.runtime_data.client.devices)
    )


class NikoClimate(NikoDeviceEntity, ClimateEntity):
    """A Niko thermostat or HVAC thermostat."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5.0
    _attr_max_temp = 30.0

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        self._attr_target_temperature_step = 1.0 if device.model == "hvacthermostat" else 0.5
        self._attr_preset_modes = (
            _HVAC_PROGRAMS.copy()
            if device.model == "hvacthermostat"
            else _STANDARD_PROGRAMS.copy()
        )
        if device.device_type == "thermostat" and "Cool" not in self._attr_preset_modes:
            self._attr_preset_modes.insert(3, "Cool")

        features = ClimateEntityFeature(0)
        if can_control(device, "Program"):
            features |= ClimateEntityFeature.PRESET_MODE
        if can_control(device, "OverruleSetpoint"):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if can_control(device, "FanSpeed"):
            features |= ClimateEntityFeature.FAN_MODE
            self._attr_fan_modes = _FAN_SPEEDS.copy()
        self._attr_supported_features = features

        if device.model == "hvacthermostat":
            self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
        else:
            self._attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO]

    @property
    def current_temperature(self) -> float | None:
        return _number(self.device.properties.get("AmbientTemperature"))

    @property
    def target_temperature(self) -> float | None:
        if str(self.device.properties.get("OverruleActive", "False")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            override = _number(self.device.properties.get("OverruleSetpoint"))
            if override is not None:
                return override
        return _number(self.device.properties.get("SetpointTemperature"))

    @property
    def preset_mode(self) -> str | None:
        value = str(self.device.properties.get("Program", ""))
        return value if value in self._attr_preset_modes else None

    @property
    def hvac_mode(self) -> HVACMode:
        if self.device.model == "hvacthermostat":
            if str(self.device.properties.get("ThermostatOn", "On")).lower() == "off":
                return HVACMode.OFF
            return (
                HVACMode.COOL
                if str(self.device.properties.get("OperationMode", "Heating")).lower()
                == "cooling"
                else HVACMode.HEAT
            )
        return HVACMode.OFF if self.preset_mode == "Off" else HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        return {
            "heating": HVACAction.HEATING,
            "cooling": HVACAction.COOLING,
        }.get(
            str(self.device.properties.get("Demand", "None")).lower(),
            HVACAction.IDLE,
        )

    @property
    def fan_mode(self) -> str | None:
        value = str(self.device.properties.get("FanSpeed", ""))
        return value if value in _FAN_SPEEDS else None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        duration = self.device.properties.get("OverruleTime", 60)
        try:
            duration = max(1, min(1439, int(float(duration))))
        except (TypeError, ValueError):
            duration = 60
        properties = {"OverruleSetpoint": str(float(temperature))}
        if can_control(self.device, "OverruleTime"):
            properties["OverruleTime"] = str(duration)
        await self.hub.async_control_device(self.device.uuid, properties)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self._attr_preset_modes:
            raise ValueError(f"Unsupported Niko program: {preset_mode}")
        await self.hub.async_control_device(
            self.device.uuid, {"Program": preset_mode}
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode not in _FAN_SPEEDS:
            raise ValueError(f"Unsupported HVAC fan speed: {fan_mode}")
        await self.hub.async_control_device(
            self.device.uuid, {"FanSpeed": fan_mode}
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if self.device.model == "hvacthermostat":
            if hvac_mode == HVACMode.OFF:
                properties = {"ThermostatOn": "Off"}
            elif hvac_mode in {HVACMode.HEAT, HVACMode.COOL}:
                properties = {
                    "ThermostatOn": "On",
                    "OperationMode": (
                        "Cooling" if hvac_mode == HVACMode.COOL else "Heating"
                    ),
                }
            else:
                raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")
        else:
            if hvac_mode == HVACMode.OFF:
                properties = {"Program": "Off"}
            elif hvac_mode == HVACMode.AUTO:
                current_program = self.preset_mode
                properties = {
                    "Program": "Day" if current_program == "Off" else current_program or "Day"
                }
            else:
                raise ValueError(f"Unsupported thermostat mode: {hvac_mode}")
        await self.hub.async_control_device(self.device.uuid, properties)
