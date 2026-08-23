from __future__ import annotations

import asyncio
import json

from custom_components.niko_home_control_local.measurements import (
    IntervalAccumulator,
    NikoMeasurement,
    NikoMeasurementsClient,
    parse_latest_measurements,
    parse_measurement_history,
)


def test_interval_accumulator_deduplicates_and_converts_wh_to_kwh() -> None:
    accumulator = IntervalAccumulator(total=2.0, last_timestamp="old")
    measurement = NikoMeasurement(500.0, "Wh", "new")

    assert accumulator.consume(measurement, divisor=1000.0) is True
    assert accumulator.total == 2.5
    assert accumulator.consume(measurement, divisor=1000.0) is False
    assert accumulator.total == 2.5


def test_interval_accumulator_ignores_negative_intervals() -> None:
    accumulator = IntervalAccumulator()

    assert accumulator.consume(NikoMeasurement(-1, "Wh", "new"), divisor=1000) is False
    assert accumulator.total is None


def test_interval_accumulator_backfills_only_newer_intervals_in_order() -> None:
    accumulator = IntervalAccumulator(total=1.0, last_timestamp="2026-01-01T00:05:00")
    added = accumulator.consume_many(
        [
            NikoMeasurement(200, "Wh", "2026-01-01T00:15:00"),
            NikoMeasurement(100, "Wh", "2026-01-01T00:10:00"),
            NikoMeasurement(999, "Wh", "2026-01-01T00:05:00"),
        ],
        divisor=1000,
    )
    assert added == 2
    assert accumulator.total == 1.3
    assert accumulator.last_timestamp == "2026-01-01T00:15:00"


def test_parse_latest_measurements_skips_invalid_values() -> None:
    result = parse_latest_measurements(
        {
            "Properties": [
                {
                    "Property": "ElectricalEnergyToGrid",
                    "Unit": "Wh",
                    "Values": [
                        {"DateTime": "2026-07-04T17:30:00Z", "Value": 7}
                    ],
                },
                {"Property": "Broken", "Values": [{"Value": "nope"}]},
            ]
        }
    )

    assert result["ElectricalEnergyToGrid"].value == 7.0
    assert result["ElectricalEnergyToGrid"].unit == "Wh"
    assert result["ElectricalEnergyToGrid"].timestamp == "2026-07-04T17:30:00Z"
    assert "Broken" not in result


def test_parse_measurement_history() -> None:
    result = parse_measurement_history(
        {
            "MeasurementProperty": "ElectricalEnergy",
            "Unit": "Wh",
            "Values": [
                {"DateTime": "2026-01-01T00:05:00", "Value": 10},
                {"DateTime": "2026-01-01T00:10:00", "Value": "20"},
            ],
        }
    )
    assert [item.value for item in result] == [10.0, 20.0]


def test_client_uses_bearer_token_and_latest_query() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return json.dumps({"Properties": []}).encode()

    calls = []

    def opener(request, **kwargs):
        calls.append((request, kwargs))
        return Response()

    client = NikoMeasurementsClient(
        host="controller.local", token="secret", opener=opener
    )
    asyncio.run(client.async_get_latest("device/1"))

    request, kwargs = calls[0]
    assert request.full_url.endswith("/devices/device%2F1?Latest=true")
    assert request.get_header("Authorization") == "Bearer secret"
    assert kwargs["timeout"] == 8.0


def test_client_builds_aggregated_history_query() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "MeasurementProperty": "ElectricalEnergy",
                    "Unit": "Wh",
                    "Values": [],
                }
            ).encode()

    calls = []

    def opener(request, **kwargs):
        calls.append(request.full_url)
        return Response()

    client = NikoMeasurementsClient(
        host="controller.local", token="secret", opener=opener
    )
    asyncio.run(
        client.async_get_aggregated_history(
            "device/1",
            "ElectricalEnergy",
            "hour",
            "2025-01-01T00:00:00+01:00",
            "2026-01-01T00:00:00+01:00",
        )
    )

    assert "/properties/ElectricalEnergy/hour?" in calls[0]
    assert "Aggregation=sum" in calls[0]
    assert "IntervalStart=" in calls[0]
    assert "IntervalEnd=" in calls[0]
