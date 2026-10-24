"""Historical Niko measurement normalization for Home Assistant statistics."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from typing import TypeVar

from .measurements import (
    NikoMeasurement,
    NikoMeasurementsClient,
    NikoMeasurementsError,
)

EARLIEST_HISTORY_YEAR = 2000
HISTORY_CHUNK_DAYS = 60
HISTORY_DAILY_CHUNK_DAYS = 90
HISTORY_HOURLY_RETENTION_DAYS = 60
HISTORY_RAW_CHUNK_DAYS = 7
HISTORY_REQUEST_ATTEMPTS = 3
HISTORY_RETRY_DELAY_SECONDS = 2

_T = TypeVar("_T")


async def _async_retry_history_request(
    request: Callable[[], Awaitable[_T]],
) -> _T:
    """Retry transient controller failures without aborting the full import."""

    for attempt in range(1, HISTORY_REQUEST_ATTEMPTS + 1):
        try:
            return await request()
        except NikoMeasurementsError:
            if attempt == HISTORY_REQUEST_ATTEMPTS:
                raise
            await asyncio.sleep(HISTORY_RETRY_DELAY_SECONDS * attempt)
    raise RuntimeError("Unreachable history retry state")


@dataclass(frozen=True, slots=True)
class HistoricalStatistic:
    """One cumulative hourly long-term statistic."""

    start: datetime
    state: float
    sum: float


def parse_niko_timestamp(value: str, local_timezone: tzinfo) -> datetime:
    """Parse a Niko local/offset timestamp and return an aware datetime."""

    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_timezone)
    return parsed


def build_hourly_statistics(
    measurements: list[NikoMeasurement],
    *,
    divisor: float,
    local_timezone: tzinfo,
) -> list[HistoricalStatistic]:
    """Aggregate historical buckets and build a monotonic cumulative series."""

    hourly_values: dict[datetime, float] = defaultdict(float)
    for measurement in measurements:
        if measurement.value < 0:
            continue
        bucket_timestamp = parse_niko_timestamp(
            measurement.timestamp, local_timezone
        ).astimezone(timezone.utc)
        # Aggregated Niko timestamps identify the start of their hour/day
        # bucket. Raw sub-hour values are grouped into their containing hour.
        hour_start = bucket_timestamp.replace(
            minute=0, second=0, microsecond=0
        )
        hourly_values[hour_start] += measurement.value / divisor

    cumulative = 0.0
    statistics: list[HistoricalStatistic] = []
    for hour_start, value in sorted(hourly_values.items()):
        cumulative += value
        statistics.append(
            HistoricalStatistic(
                start=hour_start,
                state=round(cumulative, 6),
                sum=round(cumulative, 6),
            )
        )
    return statistics


async def async_fetch_complete_hourly_history(
    client: NikoMeasurementsClient,
    device_uuid: str,
    property_name: str,
    *,
    now: datetime,
    local_timezone: tzinfo,
) -> list[NikoMeasurement]:
    """Fetch all retained values at the finest automatically available level."""

    local_now = now.astimezone(local_timezone)
    interval_end = local_now.replace(minute=0, second=0, microsecond=0)
    current_year_start = datetime(
        interval_end.year, 1, 1, tzinfo=local_timezone
    )
    first_year = interval_end.year
    if current_year_start.year > EARLIEST_HISTORY_YEAR:
        yearly = await _async_retry_history_request(
            lambda: client.async_get_aggregated_history(
                device_uuid,
                property_name,
                "year",
                datetime(EARLIEST_HISTORY_YEAR, 1, 1).isoformat(),
                current_year_start.replace(tzinfo=None).isoformat(),
            )
        )
        if yearly:
            oldest = min(
                parse_niko_timestamp(item.timestamp, local_timezone)
                for item in yearly
            )
            first_year = max(EARLIEST_HISTORY_YEAR, oldest.year - 1)

    history_start = datetime(first_year, 1, 1, tzinfo=local_timezone)
    hourly_start = max(
        history_start,
        (interval_end - timedelta(days=HISTORY_HOURLY_RETENTION_DAYS)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ),
    )

    history: list[NikoMeasurement] = []
    chunk_start = history_start
    while chunk_start < hourly_start:
        chunk_end = min(
            chunk_start + timedelta(days=HISTORY_DAILY_CHUNK_DAYS),
            hourly_start,
        )
        chunk = await _async_retry_history_request(
            lambda: client.async_get_aggregated_history(
                device_uuid,
                property_name,
                "day",
                chunk_start.replace(tzinfo=None).isoformat(),
                chunk_end.replace(tzinfo=None).isoformat(),
            )
        )
        history.extend(chunk)
        chunk_start = chunk_end

    chunk_start = hourly_start
    while chunk_start < interval_end:
        chunk_end = min(
            chunk_start + timedelta(days=HISTORY_CHUNK_DAYS),
            interval_end,
        )
        chunk = await _async_retry_history_request(
            lambda: client.async_get_aggregated_history(
                device_uuid,
                property_name,
                "hour",
                chunk_start.replace(tzinfo=None).isoformat(),
                chunk_end.replace(tzinfo=None).isoformat(),
            )
        )
        history.extend(chunk)

        # Some Niko properties expose daily aggregates and raw quarter-hour
        # measurements, but return no hourly aggregates. Fetch the uncovered
        # tail as raw measurements so recent export and water history is not
        # silently lost.
        raw_start = chunk_start
        if chunk:
            latest = max(
                parse_niko_timestamp(item.timestamp, local_timezone)
                for item in chunk
            )
            raw_start = max(
                raw_start,
                latest.replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=1),
            )
        raw_chunk_start = raw_start
        while raw_chunk_start < chunk_end:
            raw_chunk_end = min(
                raw_chunk_start + timedelta(days=HISTORY_RAW_CHUNK_DAYS),
                chunk_end,
            )
            raw_chunk = await _async_retry_history_request(
                lambda: client.async_get_history(
                    device_uuid,
                    property_name,
                    raw_chunk_start.replace(tzinfo=None).isoformat(),
                    raw_chunk_end.replace(tzinfo=None).isoformat(),
                )
            )
            history.extend(raw_chunk)
            raw_chunk_start = raw_chunk_end
        chunk_start = chunk_end

    # Be defensive against overlapping chunk boundaries and controller retries.
    unique = {measurement.timestamp: measurement for measurement in history}
    return sorted(unique.values(), key=lambda item: item.timestamp)
