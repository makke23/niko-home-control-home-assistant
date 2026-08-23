"""Niko Hobby API models and payload parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PropertyDefinition:
    """Description of one Niko device property."""

    name: str
    description: str | None = None
    has_status: bool = False
    can_control: bool = False
    has_stream: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NikoDevice:
    """A device returned by devices.list."""

    uuid: str
    name: str
    model: str = ""
    device_type: str = ""
    technology: str | None = None
    identifier: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    property_definitions: dict[str, PropertyDefinition] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class NikoNotification:
    """A notification published by the Niko controller."""

    uuid: str
    time_occurred: str
    notification_type: str
    status: str
    text: str


def _as_bool(value: Any) -> bool:
    """Convert Niko string/bool values to bool without Python truthiness traps."""

    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_device(raw: dict[str, Any]) -> NikoDevice:
    """Parse one raw Niko device dictionary."""

    uuid = str(raw.get("Uuid", "")).strip()
    if not uuid:
        raise ValueError("Niko device has no Uuid")

    device = NikoDevice(
        uuid=uuid,
        name=str(raw.get("Name") or uuid),
        model=str(raw.get("Model") or ""),
        device_type=str(raw.get("Type") or ""),
        technology=raw.get("Technology"),
        identifier=raw.get("Identifier"),
        raw=raw,
    )

    for item in raw.get("Parameters", []) or []:
        if isinstance(item, dict):
            device.parameters.update(item)

    for item in raw.get("Properties", []) or []:
        if isinstance(item, dict):
            device.properties.update(item)

    for item in raw.get("PropertyDefinitions", []) or []:
        if not isinstance(item, dict):
            continue
        for name, info in item.items():
            details = info if isinstance(info, dict) else {}
            device.property_definitions[name] = PropertyDefinition(
                name=name,
                description=details.get("Description"),
                has_status=_as_bool(details.get("HasStatus", False)),
                can_control=_as_bool(details.get("CanControl", False)),
                has_stream=_as_bool(details.get("HasStream", False)),
                raw=details,
            )

    return device


def parse_devices_list(payload: dict[str, Any]) -> dict[str, NikoDevice]:
    """Parse a complete devices.list response, keyed by UUID."""

    devices: dict[str, NikoDevice] = {}
    for param in payload.get("Params", []) or []:
        if not isinstance(param, dict):
            continue
        for raw in param.get("Devices", []) or []:
            if not isinstance(raw, dict):
                continue
            device = parse_device(raw)
            devices[device.uuid] = device
    return devices


def parse_notifications(payload: dict[str, Any]) -> list[NikoNotification]:
    """Parse notifications.list and notifications.raised payloads."""

    notifications: list[NikoNotification] = []
    for param in payload.get("Params", []) or []:
        if not isinstance(param, dict):
            continue
        for raw in param.get("Notifications", []) or []:
            if not isinstance(raw, dict):
                continue
            uuid = str(raw.get("Uuid") or "").strip()
            if not uuid:
                continue
            notification_type = str(raw.get("Type") or "notification").lower()
            if notification_type not in {"alarm", "notification"}:
                notification_type = "notification"
            notifications.append(
                NikoNotification(
                    uuid=uuid,
                    time_occurred=str(raw.get("TimeOccurred") or ""),
                    notification_type=notification_type,
                    status=str(raw.get("Status") or ""),
                    text=str(raw.get("Text") or ""),
                )
            )
    return notifications
