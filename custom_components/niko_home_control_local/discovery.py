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
        NikoAccumulationDescription("ElectricalEnergy", "Energie totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyFromGrid", "Netafname totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyToGrid", "Netinjectie totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyConsumption", "Verbruik totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyProduction", "Productie totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergySelfConsumption", "Zelfverbruik totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyCharged", "Batterij geladen totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("ElectricalEnergyDischarged", "Batterij ontladen totaal", "kWh", "energy", 1000.0),
        NikoAccumulationDescription("WaterVolume", "Waterverbruik totaal", "m³", "water", 1.0),
        NikoAccumulationDescription("GasVolume", "Gasverbruik totaal", "m³", "gas", 1.0),
        NikoAccumulationDescription("Gasvolume", "Gasverbruik totaal", "m³", "gas", 1.0),
    )
}


SENSOR_DESCRIPTIONS = {
    description.property_name: description
    for description in (
        NikoSensorDescription(
            "ElectricalPower", "Vermogen", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPower1", "Vermogen fase 1", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPower2", "Vermogen fase 2", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPower3", "Vermogen fase 3", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPowerFromGrid", "Netafname", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPowerToGrid", "Netinjectie", "W", "power", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalPeakPowerFromGrid",
            "Piek netafname",
            "W",
            "power",
            "measurement",
        ),
        NikoSensorDescription(
            "ElectricalPeakPowerToGrid",
            "Piek netinjectie",
            "W",
            "power",
            "measurement",
        ),
        NikoSensorDescription(
            "ElectricalMonthlyPeakPowerFromGrid",
            "Maandpiek",
            "W",
            "power",
            "measurement",
        ),
        NikoSensorDescription(
            "AmbientTemperature", "Temperatuur", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "HeatIndex", "Gevoelstemperatuur", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "Humidity", "Luchtvochtigheid", "%", "humidity", "measurement"
        ),
        NikoSensorDescription(
            "OutdoorTemperature", "Buitentemperatuur", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "SetpointTemperature", "Doeltemperatuur", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription(
            "OverruleSetpoint", "Tijdelijke doeltemperatuur", "°C", "temperature", "measurement"
        ),
        NikoSensorDescription("CO2", "CO₂", "ppm", "carbon_dioxide", "measurement"),
        NikoSensorDescription(
            "DomesticHotWaterTemperature",
            "Warmwatertemperatuur",
            "°C",
            "temperature",
            "measurement",
        ),
        NikoSensorDescription(
            "TargetDistance", "Doelafstand", "km", "distance", "measurement"
        ),
        NikoSensorDescription(
            "ReachableDistance", "Bereikbare afstand", "km", "distance", "measurement"
        ),
        NikoSensorDescription(
            "ElectricalEnergy", "Elektrische energie", "Wh", "energy", "total"
        ),
        NikoSensorDescription(
            "ElectricalEnergyCharged", "Geladen energie", "Wh", "energy", "total"
        ),
        NikoSensorDescription(
            "ElectricalEnergyDischarged",
            "Ontladen energie",
            "Wh",
            "energy",
            "total",
        ),
        NikoSensorDescription(
            "ElectricalEnergyFromGrid",
            "Energie van het net",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergyToGrid",
            "Energie naar het net",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergyProduction",
            "Geproduceerde energie",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergySelfConsumption",
            "Zelfverbruik",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "ElectricalEnergyConsumption",
            "Energieverbruik",
            "Wh",
            "energy",
            "total_increasing",
        ),
        NikoSensorDescription(
            "WaterVolume", "Waterverbruik", "m³", "water", "total_increasing"
        ),
        NikoSensorDescription(
            "GasVolume", "Gasverbruik", "m³", "gas", "total_increasing"
        ),
        NikoSensorDescription(
            "Gasvolume", "Gasverbruik", "m³", "gas", "total_increasing"
        ),
    )
}


ENUM_SENSOR_DESCRIPTIONS = {
    description.property_name: description
    for description in (
        NikoEnumSensorDescription(
            "Chargingstatus",
            "Laadstatus",
            ("Active", "Inactive", "BatteryFull", "Error"),
        ),
        NikoEnumSensorDescription(
            "EVStatus",
            "Voertuigstatus",
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
                        "TargetReached", "Laaddoel bereikt", None, False
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
                        "AllStarted", "Alle deelnemers actief", None, True
                    ),
                )
            )
        if device.model in _COVER_MODELS and "Aligned" in device.properties:
            discovered.append(
                (
                    device,
                    NikoBinaryDescription("Aligned", "Uitgelijnd", None, True),
                )
            )
        status_property = {
            "generic": ("StartActive", "Actief"),
            "condition": ("BasicState", "Voorwaarde waar"),
            "timeschedule": ("Active", "Actief"),
        }.get(device.model)
        if status_property is not None and status_property[0] in device.properties:
            discovered.append(
                (device, NikoBinaryDescription(status_property[0], status_property[1]))
            )
        for property_name, name, device_class, on_values in (
            ("CallPending", "Oproep actief", "sound", ("true", "on", "1")),
            ("CallAnswered", "Oproep beantwoord", None, ("true", "on", "1")),
            ("Doorlock", "Deur ontgrendeld", "lock", ("open",)),
            ("AllOffActive", "Alles-uit actief", None, ("true", "on", "1")),
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
                        "CouplingStatus", "Partnerverbinding", "connectivity", True, ("ok",)
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
                            f"Deurbel {property_name.removeprefix('CallStatus')}",
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
