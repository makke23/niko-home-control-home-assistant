from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from custom_components.niko_home_control_local.history import (
    HISTORY_REQUEST_ATTEMPTS,
    async_fetch_complete_hourly_history,
    build_hourly_statistics,
    parse_niko_timestamp,
)
from custom_components.niko_home_control_local.measurements import (
    NikoMeasurement,
    NikoMeasurementsError,
)


def test_parse_niko_timestamp_assigns_controller_timezone() -> None:
    local_timezone = timezone(timedelta(hours=1))
    parsed = parse_niko_timestamp(
        "2026-01-15T12:00:00", local_timezone
    )
    assert parsed.utcoffset().total_seconds() == 3600


def test_build_hourly_statistics_groups_and_accumulates() -> None:
    statistics = build_hourly_statistics(
        [
            NikoMeasurement(100, "Wh", "2026-01-15T01:30:00+01:00"),
            NikoMeasurement(200, "Wh", "2026-01-15T01:45:00+01:00"),
            NikoMeasurement(500, "Wh", "2026-01-15T02:15:00+01:00"),
            NikoMeasurement(-10, "Wh", "2026-01-15T03:15:00+01:00"),
        ],
        divisor=1000,
        local_timezone=timezone(timedelta(hours=1)),
    )

    assert len(statistics) == 2
    assert statistics[0].state == 0.3
    assert statistics[0].sum == 0.3
    assert statistics[1].state == 0.8
    assert statistics[1].sum == 0.8
    assert statistics[0].start.tzinfo is timezone.utc


def test_fetch_complete_history_discovers_oldest_year_and_deduplicates() -> None:
    class Client:
        def __init__(self) -> None:
            self.calls = []

        async def async_get_aggregated_history(
            self,
            device_uuid,
            property_name,
            interval,
            interval_start,
            interval_end,
            *,
            aggregation="sum",
        ):
            self.calls.append((interval, interval_start, interval_end))
            if interval == "year":
                return []
            if interval_start.startswith("2026-01-01"):
                return [
                    NikoMeasurement(20, "Wh", "2026-01-01T01:00:00+01:00"),
                    NikoMeasurement(20, "Wh", "2026-01-01T01:00:00+01:00"),
                ]
            return []

    client = Client()
    result = asyncio.run(
        async_fetch_complete_hourly_history(
            client,
            "device",
            "ElectricalEnergy",
            now=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
            local_timezone=timezone(timedelta(hours=2)),
        )
    )

    assert [measurement.value for measurement in result] == [20]
    assert client.calls[0][0] == "year"
    hourly_calls = [call for call in client.calls if call[0] == "hour"]
    daily_calls = [call for call in client.calls if call[0] == "day"]
    assert daily_calls
    assert hourly_calls
    for _, start, end in daily_calls:
        duration = datetime.fromisoformat(end) - datetime.fromisoformat(start)
        assert duration.days <= 90
    for _, start, end in hourly_calls:
        duration = datetime.fromisoformat(end) - datetime.fromisoformat(start)
        assert duration.days <= 60


def test_fetch_complete_history_retries_transient_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "custom_components.niko_home_control_local.history.HISTORY_RETRY_DELAY_SECONDS",
        0,
    )

    class Client:
        def __init__(self) -> None:
            self.attempts = 0

        async def async_get_aggregated_history(
            self, device_uuid, property_name, interval, interval_start,
            interval_end, *, aggregation="sum"
        ):
            del device_uuid, property_name, interval_start, interval_end, aggregation
            if interval == "year":
                self.attempts += 1
                if self.attempts < HISTORY_REQUEST_ATTEMPTS:
                    raise NikoMeasurementsError("temporary timeout")
            return []

    client = Client()
    result = asyncio.run(
        async_fetch_complete_hourly_history(
            client,
            "device",
            "ElectricalEnergy",
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
            local_timezone=timezone.utc,
        )
    )

    assert result == []
    assert client.attempts == HISTORY_REQUEST_ATTEMPTS
