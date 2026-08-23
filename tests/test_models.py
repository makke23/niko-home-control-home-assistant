from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "niko_home_control_local"
    / "models.py"
)
SPEC = importlib.util.spec_from_file_location("niko_native_models", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODELS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODELS
SPEC.loader.exec_module(MODELS)
parse_devices_list = MODELS.parse_devices_list


def test_parse_devices_list() -> None:
    payload = {
        "Method": "devices.list",
        "Params": [
            {
                "Devices": [
                    {
                        "Uuid": "abc",
                        "Name": "Test lamp",
                        "Model": "light",
                        "Type": "action",
                        "Properties": [{"Status": "On"}],
                        "PropertyDefinitions": [
                            {
                                "Status": {
                                    "HasStatus": "true",
                                    "CanControl": "true",
                                }
                            }
                        ],
                    }
                ]
            }
        ],
    }

    devices = parse_devices_list(payload)
    assert list(devices) == ["abc"]
    device = devices["abc"]
    assert device.name == "Test lamp"
    assert device.properties["Status"] == "On"
    assert device.property_definitions["Status"].has_status is True
    assert device.property_definitions["Status"].can_control is True


def test_duplicate_uuid_last_snapshot_entry_wins() -> None:
    payload = {
        "Params": [
            {
                "Devices": [
                    {"Uuid": "same", "Name": "Old"},
                    {"Uuid": "same", "Name": "New"},
                ]
            }
        ]
    }
    assert parse_devices_list(payload)["same"].name == "New"


def test_parse_notifications_ignores_invalid_records_and_normalizes_type() -> None:
    parsed = MODELS.parse_notifications(
        {
            "Params": [
                {
                    "Notifications": [
                        {
                            "Uuid": "one",
                            "TimeOccurred": "20260822120000",
                            "Type": "alarm",
                            "Status": "new",
                            "Text": "Beweging",
                        },
                        {"Uuid": "two", "Type": "unexpected"},
                        {"Text": "missing uuid"},
                    ]
                }
            ]
        }
    )

    assert [(item.uuid, item.notification_type) for item in parsed] == [
        ("one", "alarm"),
        ("two", "notification"),
    ]
