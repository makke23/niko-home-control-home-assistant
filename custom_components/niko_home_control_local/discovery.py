"""Capability-driven discovery rules for Niko Home Control devices."""

from __future__ import annotations

from dataclasses import dataclass

from .models import NikoDevice

_LIGHT_MODELS = {"dimmer", "light"}
_SWITCH_MODELS = {"flag", "socket", "switched-fan", "switched-generic"}
_COVER_MODELS = {
    "gate",
    "reynaers",
    "rolldownshutter",
    "sunblind",
    "velux",
    "venetianblind",
}


@dataclass(frozen=True, slots=True)
class NikoSensorDescription:
    """Description of a Niko property exposed as a Home Assistant sensor."""

    property_name: str
    name: str
    unit: str
    device_class: str
    state_class: str


@dataclass(frozen=True, slots=True)
class NikoAccumulationDescription:
    """Description of an interval measurement accumulated by Home Assistant."""

    property_name: str
    name: str
    unit: str
    device_class: str
    divisor: float


@dataclass(frozen=True, slots=True)
class NikoEnumSensorDescription:
    """Description of one textual Niko status exposed as an enum sensor."""

    property_name: str
    name: str
    options: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NikoBinaryDescription:
    """Description of one boolean action status."""

    property_name: str
    name: str
    device_class: str | None = None
    diagnostic: bool = False
    on_values: tuple[str, ...] = ("true", "on", "1")


ACCUMULATION_DESCRIPTIONS = {
    description.property_name: description
    for description in (
        NikoAccumulationDescription("ElectricalEnergy", "Total energy", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyFromGrid", "Total grid consumption", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyToGrid", "Total grid export", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyConsumption", "Total consumption", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyProduction", "Total production", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergySelfConsumption", "Total self-consumption", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyCharged", "Total battery charge", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyDischarged", "Total battery discharge", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("WaterVolume", "Total water consumption", "m³", "water", 1.0),
        NikoAccumulationDescription("GasVolume", "Total gas consumption", "m³", "gas", 1.0),
        NikoAccumulationDescription("Gasvolume", "Total gas consumption", "m³", "gas", 1.0),
    )
}


SENSOR_DESCRIPTIONS = {
    description.property_name: description
    for description in (
        NikoSensorDescription(
            "ElectricalPower", "Power", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPower1", "Phase 1 power", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPower2", "Phase 2 power", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPower3", "Phase 3 power", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPowerFromGrid", "Grid consumption", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPowerToGrid", "Grid export", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPeakPowerFromGrid",
            "Peak grid consumption",
            "W",
            "power",
            "measurement",
        ),
        NikoSensorDescription(
            "ElectricalPeakPowerToGrid",
            "Peak grid export",
            "W",
            "power",
            "measurement",
        ),
        NikoSensorDescription(
            "ElectricalMonthlyPeakPowerFromGrid",
            "Monthly peak",
            "W",
            "power",
            "measurement",
        ),
        NikoSensorDescription(
            "AmbientTemperature", "Temperature", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "HeatIndex", "Feels-like temperature", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "Humidity", "Humidity", "%", "humidity", "measurement"
        ),
        NikoSensorDescription(
            "OutdoorTemperature", "Outdoor temperature", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "SetpointTemperature", "Target temperature", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "OverruleSetpoint", "Temporary target temperature", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription("CO2", "CO₂", "ppm", "carbon_dioxide", "measurement"),
        NikoSensorDescription(
            "DomesticHotWaterTemperature",
            "Domestic hot water temperature",
            "°C",
            "temperature",
            "measurement",
        ),
        NikoSensorDescription(
            "TargetDistance", "Target distance", "km", "distance", "measurement"
        ),
        NikoSensorDescription(
            "ReachableDistance", "Reachable distance", "km", "distance", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalEnergy", "Electrical energy", "Wh", "energy", "total"
        ),
        NikoSensorDescription(
            "ElectricalEnergyCharged", "Charged energy", "Wh", "energy", "total"
        ),
        NikoSensorDescription(
            "ElectricalEnergyDischarged",
            "Discharged energy",
            "Wh",
            "energy",
            "total",
        ),
        NikoSensorDescription(
            "ElectricalEnergyFromGrid",
            "Energy from grid",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergyToGrid",
            "Energy to grid",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergyProduction",
            "Produced energy",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergySelfConsumption",
            "Self-consumption",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergyConsumption",
            "Energy consumption",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "WaterVolume", "Water consumption", "m³", "water", "total_increasing"
        ),
        NikoSensorDescription(
            "GasVolume", "Gas consumption", "m³", "gas", "total_increasing"
        ),
        NikoSensorDescription(
            "Gasvolume", "Gas consumption", "m³", "gas", "total_increasing"
        ),
    )
}


ENUM_SENSOR_DESCRIPTIONS = {
    description.property_name: description
    for description in (
        NikoEnumSensorDescription(
            "Chargingstatus",
            "Charging status",
            ("Active", "Inactive", "BatteryFull", "Error"),
        ),
        NikoEnumSensorDescription(
            "EVStatus",
            "Vehicle status",
            ("Idle", "Connected", "Charging", "Error"),
        ),
    )
}


def can_control(device: NikoDevice, property_name: str) -> bool:
    """Return whether a device property is explicitly controllable."""

    definition = device.property_definitions.get(property_name)
    return definition is not None and definition.can_control


def discover_lights(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return user-facing Niko light and dimmer actions."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action"
        and device.model in _LIGHT_MODELS
        and can_control(device, "Status")
    ]


def discover_switches(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return user-facing relay actions, excluding internal hardware records."""

    return [
        device
        for device in devices.values()
        if (
            (device.device_type == "action" and device.model in _SWITCH_MODELS)
            or device.device_type == "chargingstation"
        )
        and can_control(device, "Status")
    ]


def discover_boost_switches(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return partner devices with a controllable boost property."""

    return [device for device in devices.values() if can_control(device, "Boost")]


def discover_toggle_actions(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return stateful actions toggled with BasicState=Triggered."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action"
        and device.model
        in {
            "alarms",
            "generic",
            "overallcomfort",
            "peakmode",
            "pir",
            "simulation",
            "solarmode",
        }
        and can_control(device, "BasicState")
    ]


def discover_trigger_buttons(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return stateless actions executed with BasicState=Triggered."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action"
        and device.model in {"alloff", "condition", "panic"}
        and can_control(device, "BasicState")
    ]


def discover_scenes(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return Niko mood actions represented as Home Assistant scenes."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action"
        and device.model in {"comfort", "mood"}
        and can_control(device, "BasicState")
    ]


def discover_door_unlock_actions(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return access-control actions capable of opening a door lock."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action" and can_control(device, "Doorlock")
    ]


def discover_fan_speed_actions(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return Niko fan actions with an explicitly controllable speed."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action"
        and device.model == "fan"
        and can_control(device, "FanSpeed")
    ]


def discover_climate_devices(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return Niko thermostat devices with a reported ambient temperature."""

    discovered: list[NikoDevice] = []
    for device in devices.values():
        if device.device_type not in {"hvac", "thermostat"}:
            continue
        available = set(device.properties)
        available.update(
            name
            for name, definition in device.property_definitions.items()
            if definition.has_status
        )
        if "AmbientTemperature" in available:
            discovered.append(device)
    return discovered


def discover_partner_fans(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return generic partner ventilation devices."""

    return [device for device in devices.values() if device.device_type == "fan"]


def discover_audio_actions(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return Niko audio-control actions."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action" and device.model == "audiocontrol"
    ]


def discover_hot_water_devices(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return generic domestic hot-water devices."""

    return [
        device
        for device in devices.values()
        if device.device_type == "domestichotwaterunit"
    ]


def discover_charging_mode_devices(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return EV chargers with a controllable charging mode."""

    return [
        device
        for device in devices.values()
        if device.device_type == "chargingstation"
        and can_control(device, "Chargingmode")
    ]


def discover_binary_statuses(
    devices: dict[str, NikoDevice],
) -> list[tuple[NikoDevice, NikoBinaryDescription]]:
    """Return meaningful boolean status values for Niko actions."""

    discovered: list[tuple[NikoDevice, NikoBinaryDescription]] = []
    for device in devices.values():
        if device.device_type == "chargingstation" and "TargetReached" in device.properties:
            discovered.append(
                (
                    device,
                    NikoBinaryDescription(
                        "TargetReached", "Charging target reached", None, False
                    ),
                )
            )
        if device.device_type != "action":
            continue
        if "AllConnected" in device.properties:
            discovered.append(
                (
                    device,
                    NikoBinaryDescription(
                        "AllConnected", "Verbonden", "connectivity", True
                    ),
                )
            )
        if "AllStarted" in device.properties:
            discovered.append(
                (
                    device,
                    NikoBinaryDescription(
                        "AllStarted", "All participants active", None, True
                    ),
                )
            )
        if device.model in _COVER_MODELS and "Aligned" in device.properties:
            discovered.append(
                (
                    device,
                    NikoBinaryDescription("Aligned", "Aligned", None, True),
                )
            )
        status_property = {
            "generic": ("StartActive", "Active"),
            "condition": ("BasicState", "Condition true"),
            "timeschedule": ("Active", "Active"),
        }.get(device.model)
        if status_property is not None and status_property[0] in device.properties:
            discovered.append(
                (device, NikoBinaryDescription(status_property[0], status_property[1]))
            )
        for property_name, name, device_class, on_values in (
            ("CallPending", "Call active", "sound", ("true", "on", "1")),
            ("CallAnswered", "Call answered", None, ("true", "on", "1")),
            ("Doorlock", "Door unlocked", "lock", ("open",)),
            ("AllOffActive", "All-off active", None, ("true", "on", "1")),
        ):
            if property_name in device.properties:
                discovered.append(
                    (
                        device,
                        NikoBinaryDescription(
                            property_name,
                            name,
                            device_class,
                            False,
                            on_values,
                        ),
                    )
                )
        coupling_status = device.properties.get("CouplingStatus")
        if coupling_status is not None:
            discovered.append(
                (
                    device,
                    NikoBinaryDescription(
                        "CouplingStatus",
                        "Partner connection",
                        "connectivity",
                        True,
                        ("ok",),
                    ),
                )
            )
        for property_name in sorted(device.properties):
            if property_name.startswith("CallStatus"):
                discovered.append(
                    (
                        device,
                        NikoBinaryDescription(
                            property_name,
                            f"Doorbell {property_name.removeprefix('CallStatus')}",
                            "sound",
                            False,
                            ("ringing", "active"),
                        ),
                    )
                )
    return discovered


def discover_covers(devices: dict[str, NikoDevice]) -> list[NikoDevice]:
    """Return user-facing motor actions supported by Home Assistant covers."""

    return [
        device
        for device in devices.values()
        if device.device_type == "action"
        and device.model in _COVER_MODELS
        and can_control(device, "Action")
    ]


def discover_sensors(
    devices: dict[str, NikoDevice],
) -> list[tuple[NikoDevice, NikoSensorDescription]]:
    """Return supported status properties exposed as numeric sensors."""

    discovered: list[tuple[NikoDevice, NikoSensorDescription]] = []
    for device in devices.values():
        status_properties = set(device.properties)
        status_properties.update(
            property_name
            for property_name, definition in device.property_definitions.items()
            if definition.has_status
        )
        discovered.extend(
            (device, SENSOR_DESCRIPTIONS[property_name])
            for property_name in SENSOR_DESCRIPTIONS
            if property_name in status_properties
        )
    return discovered


def discover_enum_sensors(
    devices: dict[str, NikoDevice],
) -> list[tuple[NikoDevice, NikoEnumSensorDescription]]:
    """Return supported textual device statuses as enum sensors."""

    discovered: list[tuple[NikoDevice, NikoEnumSensorDescription]] = []
    for device in devices.values():
        status_properties = set(device.properties)
        status_properties.update(
            property_name
            for property_name, definition in device.property_definitions.items()
            if definition.has_status
        )
        discovered.extend(
            (device, ENUM_SENSOR_DESCRIPTIONS[property_name])
            for property_name in ENUM_SENSOR_DESCRIPTIONS
            if property_name in status_properties
        )
    return discovered


def discover_accumulated_measurements(
    devices: dict[str, NikoDevice], measurements: dict[str, dict[str, object]]
) -> list[tuple[NikoDevice, NikoAccumulationDescription]]:
    """Return REST interval properties that can safely be accumulated."""

    discovered: list[tuple[NikoDevice, NikoAccumulationDescription]] = []
    for device in devices.values():
        available = set(measurements.get(device.uuid, {}))
        if (
            device.device_type in {"chargingstation", "smartplug"}
            and "ElectricalPower" in device.properties
        ):
            available.add("ElectricalEnergy")
        if device.device_type == "centralmeter":
            available.update(set(device.properties) & ACCUMULATION_DESCRIPTIONS.keys())
        discovered.extend(
            (device, description)
            for property_name, description in ACCUMULATION_DESCRIPTIONS.items()
            if property_name in available
        )
    return discovered
