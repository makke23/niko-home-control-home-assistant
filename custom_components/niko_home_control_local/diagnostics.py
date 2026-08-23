"""Diagnostics for Niko Home Control."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_TOKEN
from .hub import NikoHub


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[NikoHub]
) -> dict[str, Any]:
    """Return privacy-safe diagnostics for a config entry."""

    del hass
    hub = entry.runtime_data
    groups = Counter(
        (device.model or "-", device.device_type or "-")
        for device in hub.client.devices.values()
    )
    return {
        "entry_data": async_redact_data(
            entry.data, {CONF_TOKEN, CONF_HOST, CONF_USERNAME}
        ),
        "connected": hub.connected,
        "device_count": hub.device_count,
        "device_groups": [
            {"model": model, "type": device_type, "count": count}
            for (model, device_type), count in sorted(groups.items())
        ],
        "measurement_device_count": len(hub.measurements),
        "history_import": {
            "status": hub.history_import_status,
            "series_expected": hub.history_import_expected,
            "series_processed": len(hub.history_import_records),
            "measurements_imported": sum(
                record.measurement_count
                for record in hub.history_import_records.values()
            ),
            "errors": [
                record.error
                for record in hub.history_import_records.values()
                if record.error
            ],
        },
        "notification_counts": dict(
            Counter(
                notification.notification_type
                for notification in hub.client.notifications.values()
            )
        ),
        "last_error": hub.last_error,
    }
