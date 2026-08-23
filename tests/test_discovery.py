from __future__ import annotations

from custom_components.niko_home_control_local.discovery import (
    discover_accumulated_measurements,
    discover_binary_statuses,
    discover_boost_switches,
    discover_charging_mode_devices,
    discover_climate_devices,
    discover_covers,
    discover_door_unlock_actions,
    discover_enum_sensors,
    discover_fan_speed_actions,
    discover_hot_water_devices,
    discover_lights,
    discover_audio_actions,
    discover_partner_fans,
    discover_scenes,
    discover_sensors,
    discover_switches,
    discover_toggle_actions,
    discover_trigger_buttons,
)
from custom_components.niko_home_control_local.measurements import NikoMeasurement
from custom_components.niko_home_control_local.models import (
    NikoDevice,
    PropertyDefinition,
)


def _device(
    uuid: str,
    *,
    model: str,
    device_type: str,
    controls: tuple[str, ...],
) -> NikoDevice:
    return NikoDevice(
        uuid=uuid,
        name=uuid,
        model=model,
        device_type=device_type,
        property_definitions={
            name: PropertyDefinition(name=name, can_control=True) for name in controls
        },
    )


def test_discovers_user_facing_actions_and_ignores_internal_hardware() -> None:
    devices = {
        "light-action": _device(
            "light-action", model="light", device_type="action", controls=("Status",)
        ),
        "relay": _device(
            "relay", model="light", device_type="smartrelay", controls=()
        ),
        "socket-action": _device(
            "socket-action",
            model="socket",
            device_type="action",
            controls=("Status",),
        ),
        "smartplug": _device(
            "smartplug", model="naso", device_type="smartplug", controls=("Status",)
        ),
        "cover-action": _device(
            "cover-action",
            model="rolldownshutter",
            device_type="action",
            controls=("Action", "Position"),
        ),
        "motor": _device(
            "motor", model="rolldownshutter", device_type="smartmotor", controls=()
        ),
    }

    assert [device.uuid for device in discover_lights(devices)] == ["light-action"]
    assert [device.uuid for device in discover_switches(devices)] == [
        "socket-action"
    ]
    assert [device.uuid for device in discover_covers(devices)] == ["cover-action"]


def test_discovers_only_supported_numeric_sensor_properties() -> None:
    power_device = _device(
        "smartplug", model="naso", device_type="smartplug", controls=()
    )
    power_device.properties = {
        "ElectricalPower": "123.5",
        "Status": "On",
    }
    energy_device = _device(
        "energy", model="generic", device_type="energyhome", controls=()
    )
    energy_device.properties = {
        "ElectricalPowerFromGrid": 250,
        "ElectricalPowerToGrid": 0,
        "ElectricalMonthlyPeakPowerFromGrid": 3100,
    }

    discovered = discover_sensors(
        {power_device.uuid: power_device, energy_device.uuid: energy_device}
    )

    assert [
        (device.uuid, description.property_name)
        for device, description in discovered
    ] == [
        ("smartplug", "ElectricalPower"),
        ("energy", "ElectricalPowerFromGrid"),
        ("energy", "ElectricalPowerToGrid"),
        ("energy", "ElectricalMonthlyPeakPowerFromGrid"),
    ]


def test_discovers_declared_meter_status_before_first_value_arrives() -> None:
    meter = _device(
        "meter", model="electricity-clamp", device_type="centralmeter", controls=()
    )
    meter.property_definitions = {
        "ElectricalPower1": PropertyDefinition(
            name="ElectricalPower1", has_status=True
        ),
        "ElectricalEnergy": PropertyDefinition(
            name="ElectricalEnergy", has_status=True
        ),
        "InternalValue": PropertyDefinition(name="InternalValue", has_status=True),
    }

    discovered = discover_sensors({meter.uuid: meter})

    assert [description.property_name for _, description in discovered] == [
        "ElectricalPower1",
        "ElectricalEnergy",
    ]
    assert discovered[0][1].device_class == "power"
    assert discovered[0][1].state_class == "measurement"
    assert discovered[1][1].device_class == "energy"
    assert discovered[1][1].state_class == "total"


def test_discovers_water_and_gas_volume_with_total_increasing_state() -> None:
    meter = _device(
        "pulse-meter", model="water", device_type="centralmeter", controls=()
    )
    meter.properties = {"WaterVolume": "12.345", "GasVolume": "1.5"}

    discovered = discover_sensors({meter.uuid: meter})

    assert [
        (
            description.property_name,
            description.unit,
            description.device_class,
            description.state_class,
        )
        for _, description in discovered
    ] == [
        ("WaterVolume", "m³", "water", "total_increasing"),
        ("GasVolume", "m³", "gas", "total_increasing"),
    ]


def test_discovers_only_supported_rest_intervals_for_known_devices() -> None:
    energyhome = _device(
        "energyhome", model="generic", device_type="energyhome", controls=()
    )
    discovered = discover_accumulated_measurements(
        {energyhome.uuid: energyhome},
        {
            energyhome.uuid: {
                "ElectricalEnergyFromGrid": NikoMeasurement(10, "Wh", "now"),
                "WaterVolume": NikoMeasurement(0.01, "m³", "now"),
                "WaterCost": NikoMeasurement(1, "EUR", "now"),
            }
        },
    )

    assert [description.property_name for _, description in discovered] == [
        "ElectricalEnergyFromGrid",
        "WaterVolume",
    ]


def test_discovers_battery_and_gas_history_from_central_meter_capabilities() -> None:
    battery = _device(
        "battery", model="battery-clamp", device_type="centralmeter", controls=()
    )
    battery.properties = {
        "ElectricalEnergyCharged": "125",
        "ElectricalEnergyDischarged": "80",
        "ElectricalPower": "450",
    }
    gas = _device(
        "gas", model="gas", device_type="centralmeter", controls=()
    )
    gas.properties = {"Gasvolume": "0.12"}

    discovered = discover_accumulated_measurements(
        {battery.uuid: battery, gas.uuid: gas},
        {},
    )

    assert [description.property_name for _, description in discovered] == [
        "ElectricalEnergyCharged",
        "ElectricalEnergyDischarged",
        "Gasvolume",
    ]
    assert [description.device_class for _, description in discovered] == [
        "energy",
        "energy",
        "gas",
    ]


def test_discovers_action_controls_and_boolean_statuses() -> None:
    generic = _device(
        "generic", model="generic", device_type="action", controls=("BasicState",)
    )
    generic.properties = {
        "BasicState": "On",
        "StartActive": "True",
        "AllConnected": "True",
        "AllStarted": "False",
    }
    pir = _device("pir", model="pir", device_type="action", controls=("BasicState",))
    pir.properties = {"BasicState": "Off"}
    condition = _device(
        "condition", model="condition", device_type="action", controls=("BasicState",)
    )
    condition.properties = {"BasicState": "On", "AllConnected": "True"}
    schedule = _device(
        "schedule", model="timeschedule", device_type="action", controls=()
    )
    schedule.properties = {"Active": "True", "AllConnected": "True"}
    devices = {
        device.uuid: device for device in (generic, pir, condition, schedule)
    }

    assert [device.uuid for device in discover_toggle_actions(devices)] == [
        "generic",
        "pir",
    ]
    assert [device.uuid for device in discover_trigger_buttons(devices)] == [
        "condition"
    ]
    assert [
        (device.uuid, description.property_name, description.diagnostic)
        for device, description in discover_binary_statuses(devices)
    ] == [
        ("generic", "AllConnected", True),
        ("generic", "AllStarted", True),
        ("generic", "StartActive", False),
        ("condition", "AllConnected", True),
        ("condition", "BasicState", False),
        ("schedule", "AllConnected", True),
        ("schedule", "Active", False),
    ]


def test_discovers_fans_and_extended_cover_models_by_capability() -> None:
    fan = _device(
        "fan", model="fan", device_type="action", controls=("FanSpeed",)
    )
    velux = _device(
        "velux", model="velux", device_type="action", controls=("Action",)
    )
    reynaers = _device(
        "reynaers", model="reynaers", device_type="action", controls=("Action",)
    )
    devices = {device.uuid: device for device in (fan, velux, reynaers)}

    assert [device.uuid for device in discover_fan_speed_actions(devices)] == [
        "fan"
    ]
    assert [device.uuid for device in discover_covers(devices)] == [
        "velux",
        "reynaers",
    ]


def test_discovers_climates_and_thermoswitch_measurements() -> None:
    thermostat = _device(
        "thermostat", model="thermostat", device_type="hvac", controls=("Program",)
    )
    thermostat.property_definitions["AmbientTemperature"] = PropertyDefinition(
        name="AmbientTemperature", has_status=True
    )
    thermostat.properties = {
        "AmbientTemperature": "20.5",
        "SetpointTemperature": "21.0",
        "OverruleSetpoint": "22.0",
    }
    switch = _device(
        "thermoswitch", model="thermoswitchx1", device_type="multisensor", controls=()
    )
    switch.properties = {
        "AmbientTemperature": "21.5",
        "HeatIndex": "22",
        "Humidity": "48.2",
    }
    devices = {device.uuid: device for device in (thermostat, switch)}

    assert [device.uuid for device in discover_climate_devices(devices)] == [
        "thermostat"
    ]
    assert [
        description.property_name for _, description in discover_sensors(devices)
    ] == [
        "AmbientTemperature",
        "SetpointTemperature",
        "OverruleSetpoint",
        "AmbientTemperature",
        "HeatIndex",
        "Humidity",
    ]


def test_discovers_scenes_access_and_partner_platforms() -> None:
    mood = _device(
        "mood", model="mood", device_type="action", controls=("BasicState",)
    )
    access = _device(
        "access", model="accesscontrol", device_type="action", controls=("Doorlock",)
    )
    audio = _device(
        "audio", model="audiocontrol", device_type="action", controls=("Playback",)
    )
    fan = _device(
        "partner-fan", model="generic", device_type="fan", controls=("FanSpeed",)
    )
    hot_water = _device(
        "hot-water",
        model="generic",
        device_type="domestichotwaterunit",
        controls=("Program",),
    )
    charger = _device(
        "charger",
        model="generic",
        device_type="chargingstation",
        controls=("Chargingmode", "Boost"),
    )
    charger.properties = {
        "Chargingstatus": "Active",
        "EVStatus": "Charging",
        "ElectricalPower": "7400",
        "TargetReached": "False",
    }
    devices = {
        device.uuid: device
        for device in (mood, access, audio, fan, hot_water, charger)
    }

    assert [device.uuid for device in discover_scenes(devices)] == ["mood"]
    assert [device.uuid for device in discover_door_unlock_actions(devices)] == [
        "access"
    ]
    assert [device.uuid for device in discover_audio_actions(devices)] == ["audio"]
    assert [device.uuid for device in discover_partner_fans(devices)] == [
        "partner-fan"
    ]
    assert [device.uuid for device in discover_hot_water_devices(devices)] == [
        "hot-water"
    ]
    assert [device.uuid for device in discover_charging_mode_devices(devices)] == [
        "charger"
    ]
    assert [device.uuid for device in discover_boost_switches(devices)] == [
        "charger"
    ]
    assert [
        description.property_name
        for _, description in discover_enum_sensors(devices)
    ] == ["Chargingstatus", "EVStatus"]
    assert [
        description.property_name
        for device, description in discover_binary_statuses(devices)
        if device.uuid == "charger"
    ] == ["TargetReached"]

    accumulated = discover_accumulated_measurements(devices, {})
    assert [
        description.property_name
        for device, description in accumulated
        if device.uuid == "charger"
    ] == ["ElectricalEnergy"]


def test_discovers_access_alarm_and_doorbell_statuses() -> None:
    access = _device(
        "access", model="accesscontrol", device_type="action", controls=()
    )
    access.properties = {
        "CallPending": "On",
        "CallAnswered": "False",
        "Doorlock": "Open",
        "AllOffActive": "True",
        "CouplingStatus": "Ok",
        "CallStatus01": "Ringing",
    }

    descriptions = [
        description for _, description in discover_binary_statuses({access.uuid: access})
    ]

    assert [description.property_name for description in descriptions] == [
        "CallPending",
        "CallAnswered",
        "Doorlock",
        "AllOffActive",
        "CouplingStatus",
        "CallStatus01",
    ]
    assert descriptions[2].on_values == ("open",)
    assert descriptions[4].diagnostic is True
    assert descriptions[5].on_values == ("ringing", "active")
