"""Client and models for the local Niko measurements REST API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import ssl
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class NikoMeasurementsError(Exception):
    """Raised when the measurements endpoint cannot be read."""


@dataclass(frozen=True, slots=True)
class NikoMeasurement:
    """One latest interval value returned by the controller."""

    value: float
    unit: str
    timestamp: str


@dataclass(slots=True)
class IntervalAccumulator:
    """Deduplicate interval measurements and maintain a monotonic total."""

    total: float | None = None
    last_timestamp: str | None = None

    def consume(self, measurement: NikoMeasurement, *, divisor: float) -> bool:
        """Add a new non-negative interval and return whether state changed."""

        if measurement.timestamp == self.last_timestamp or measurement.value < 0:
            return False
        if self.total is None:
            self.total = 0.0
        self.total += measurement.value / divisor
        self.last_timestamp = measurement.timestamp
        return True

    def consume_many(
        self, measurements: list[NikoMeasurement], *, divisor: float
    ) -> int:
        """Consume chronological intervals and return the number added."""

        changed = 0
        for measurement in sorted(measurements, key=lambda item: item.timestamp):
            if self.last_timestamp is not None and measurement.timestamp <= self.last_timestamp:
                continue
            changed += self.consume(measurement, divisor=divisor)
        return changed


def parse_latest_measurements(payload: Any) -> dict[str, NikoMeasurement]:
    """Normalize the Niko latest-measurements response."""

    if not isinstance(payload, dict):
        raise NikoMeasurementsError("Measurement response is not a JSON object")
    measurements: dict[str, NikoMeasurement] = {}
    for item in payload.get("Properties", []) or []:
        if not isinstance(item, dict):
            continue
        property_name = item.get("Property")
        values = item.get("Values")
        if not isinstance(property_name, str) or not isinstance(values, list) or not values:
            continue
        latest = values[0]
        if not isinstance(latest, dict):
            continue
        try:
            value = float(latest["Value"])
        except (KeyError, TypeError, ValueError):
            continue
        timestamp = latest.get("DateTime")
        if not isinstance(timestamp, str) or not timestamp:
            continue
        measurements[property_name] = NikoMeasurement(
            value=value,
            unit=str(item.get("Unit") or ""),
            timestamp=timestamp,
        )
    return measurements


def parse_measurement_history(payload: Any) -> list[NikoMeasurement]:
    """Normalize a single-property raw measurement response."""

    if not isinstance(payload, dict):
        raise NikoMeasurementsError("Measurement history is not a JSON object")
    property_name = payload.get("MeasurementProperty") or payload.get("Property")
    if not isinstance(property_name, str):
        raise NikoMeasurementsError("Measurement history has no property")
    unit = str(payload.get("Unit") or "")
    result: list[NikoMeasurement] = []
    for raw in payload.get("Values", []) or []:
        if not isinstance(raw, dict):
            continue
        try:
            value = float(raw["Value"])
        except (KeyError, TypeError, ValueError):
            continue
        timestamp = raw.get("DateTime")
        if isinstance(timestamp, str) and timestamp:
            result.append(NikoMeasurement(value, unit, timestamp))
    return result


class NikoMeasurementsClient:
    """Read interval measurements without blocking the asyncio event loop."""

    def __init__(
        self,
        *,
        host: str,
        token: str,
        timeout: float = 8.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self._base_url = f"https://{host}/measurements/v1"
        self._token = token
        self._timeout = timeout
        self._opener = opener
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    async def async_get_latest(
        self, device_uuid: str
    ) -> dict[str, NikoMeasurement]:
        """Return the latest logged interval for every property of one device."""

        return await asyncio.to_thread(self._get_latest, device_uuid)

    async def async_get_history(
        self,
        device_uuid: str,
        property_name: str,
        interval_start: str,
        interval_end: str,
    ) -> list[NikoMeasurement]:
        """Return raw intervals after start up to and including end."""

        return await asyncio.to_thread(
            self._get_history,
            device_uuid,
            property_name,
            interval_start,
            interval_end,
        )

    async def async_get_aggregated_history(
        self,
        device_uuid: str,
        property_name: str,
        interval: str,
        interval_start: str,
        interval_end: str,
        *,
        aggregation: str = "sum",
    ) -> list[NikoMeasurement]:
        """Return aggregated intervals for one logged property."""

        if interval not in {"hour", "day", "month", "year"}:
            raise ValueError(f"Unsupported Niko measurement interval: {interval}")
        if aggregation not in {"sum", "avg", "min", "max"}:
            raise ValueError(f"Unsupported Niko aggregation: {aggregation}")
        return await asyncio.to_thread(
            self._get_history,
            device_uuid,
            property_name,
            interval_start,
            interval_end,
            interval,
            aggregation,
        )

    def _get_latest(self, device_uuid: str) -> dict[str, NikoMeasurement]:
        url = f"{self._base_url}/devices/{quote(device_uuid, safe='')}?Latest=true"
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
        )
        try:
            with self._opener(
                request, context=self._ssl_context, timeout=self._timeout
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise NikoMeasurementsError(
                f"Could not read measurements for device: {exc}"
            ) from exc
        return parse_latest_measurements(payload)

    def _get_history(
        self,
        device_uuid: str,
        property_name: str,
        interval_start: str,
        interval_end: str,
        interval: str | None = None,
        aggregation: str | None = None,
    ) -> list[NikoMeasurement]:
        query_params = {
            "IntervalStart": interval_start,
            "IntervalEnd": interval_end,
        }
        if aggregation is not None:
            query_params["Aggregation"] = aggregation
        query = urlencode(query_params)
        interval_path = f"/{quote(interval, safe='')}" if interval else ""
        url = (
            f"{self._base_url}/devices/{quote(device_uuid, safe='')}"
            f"/properties/{quote(property_name, safe='')}{interval_path}?{query}"
        )
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
        )
        try:
            with self._opener(
                request, context=self._ssl_context, timeout=self._timeout
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            except OSError:
                detail = ""
            suffix = f": {detail}" if detail else ""
            raise NikoMeasurementsError(
                f"Could not read measurement history: HTTP {exc.code}{suffix}"
            ) from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise NikoMeasurementsError(
                f"Could not read measurement history for device: {exc}"
            ) from exc
        return parse_measurement_history(payload)
