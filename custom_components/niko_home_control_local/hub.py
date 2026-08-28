"""Runtime hub shared by all Niko Home Control entities."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import logging
from typing import Any

from .const import LIVE_POWER_PROPERTIES
from .niko_client import NikoClient, NikoError
from .measurements import NikoMeasurement, NikoMeasurementsClient, NikoMeasurementsError

_LOGGER = logging.getLogger(__name__)
_INSTANT_USAGE_REFRESH_SECONDS = 25
_INSTANT_USAGE_STALE_SECONDS = 90
_MEASUREMENT_REFRESH_SECONDS = 300
_MEASUREMENT_DEVICE_TYPES = {
    "centralmeter",
    "chargingstation",
    "energyhome",
    "smartplug",
}


@dataclass(slots=True, frozen=True)
class NikoHubConfig:
    """Immutable controller settings from a Home Assistant config entry."""

    host: str
    port: int
    username: str
    token: str
    client_id: str


@dataclass(slots=True, frozen=True)
class HistoricalImportRecord:
    """Result of one accumulated sensor's historical import."""

    status: str
    measurement_count: int = 0
    earliest: str | None = None
    latest: str | None = None
    error: str | None = None


class NikoHub:
    """Coordinate the Niko client and Home Assistant entities."""

    def __init__(self, config: NikoHubConfig) -> None:
        self.config = config
        self._instant_usage_task: asyncio.Task[None] | None = None
        self._measurement_task: asyncio.Task[None] | None = None
        self.measurements: dict[str, dict[str, NikoMeasurement]] = {}
        self.history_import_expected = 0
        self.history_import_records: dict[str, HistoricalImportRecord] = {}
        # The controller's measurements API becomes unreliable when several
        # large history queries run in parallel. Import series sequentially.
        self.history_import_semaphore = asyncio.Semaphore(1)
        self.measurements_client = NikoMeasurementsClient(
            host=config.host, token=config.token, timeout=45.0
        )
        self.client = NikoClient(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.token,
            client_id=config.client_id,
        )

    @property
    def identifier(self) -> str:
        return f"{self.config.host}:{self.config.port}"

    @property
    def connected(self) -> bool:
        return self.client.connected

    @property
    def device_count(self) -> int:
        return len(self.client.devices)

    @property
    def last_error(self) -> str | None:
        return self.client.last_error

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        return self.client.add_listener(listener)

    def set_history_import_expected(self, count: int) -> None:
        """Set the number of historical measurement series to process."""

        self.history_import_expected = count

    def update_history_import(
        self, key: str, record: HistoricalImportRecord
    ) -> None:
        """Store import progress and update diagnostic entities."""

        self.history_import_records[key] = record
        self.client.notify_listeners()

    @property
    def history_import_status(self) -> str:
        """Return the aggregate historical import status."""

        if self.history_import_expected == 0:
            return "not_applicable"
        records = list(self.history_import_records.values())
        if any(record.status == "running" for record in records):
            return "running"
        if len(records) < self.history_import_expected:
            return "pending"
        if records and all(record.status == "error" for record in records):
            return "failed"
        if any(record.status == "error" for record in records):
            return "partial"
        return "completed"

    async def async_setup(self) -> None:
        await self.client.async_start()
        try:
            await self.client.async_request_notifications()
        except NikoError as exc:
            _LOGGER.debug("Could not retrieve Niko notifications: %s", exc)
        await self.async_refresh_measurements()
        self._measurement_task = asyncio.create_task(
            self._async_measurement_loop(), name="niko_measurements_refresh"
        )
        if self._instant_usage_devices():
            self._instant_usage_task = asyncio.create_task(
                self._async_keep_instant_usage_enabled(),
                name="niko_instant_usage_refresh",
            )

    async def async_shutdown(self) -> None:
        if self._measurement_task is not None:
            self._measurement_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._measurement_task
            self._measurement_task = None
        if self._instant_usage_task is not None:
            self._instant_usage_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._instant_usage_task
            self._instant_usage_task = None
        await self.client.async_stop()

    async def async_refresh_devices(self) -> None:
        await self.client.async_request_devices()

    async def async_control_device(
        self, device_uuid: str, properties: dict[str, Any]
    ) -> None:
        await self.client.async_control_device(device_uuid, properties)

    async def async_refresh_measurements(self) -> None:
        """Refresh latest interval values for devices that expose logged data."""

        candidates = [
            device
            for device in self.client.devices.values()
            if device.device_type.lower() in _MEASUREMENT_DEVICE_TYPES
        ]
        results = await asyncio.gather(
            *(self.measurements_client.async_get_latest(device.uuid) for device in candidates),
            return_exceptions=True,
        )
        changed = False
        for device, result in zip(candidates, results, strict=True):
            if isinstance(result, NikoMeasurementsError):
                _LOGGER.debug("Could not refresh measurements for %s: %s", device.name, result)
                continue
            if isinstance(result, BaseException):
                _LOGGER.debug("Unexpected measurement error for %s: %s", device.name, result)
                continue
            if result:
                self.measurements[device.uuid] = result
                changed = True
        if changed:
            self.client.notify_listeners()

    async def _async_measurement_loop(self) -> None:
        while True:
            await asyncio.sleep(_MEASUREMENT_REFRESH_SECONDS)
            await self.async_refresh_measurements()

    def _instant_usage_devices(self) -> list[str]:
        device_uuids: list[str] = []
        for device in self.client.devices.values():
            definition = device.property_definitions.get("ReportInstantUsage")
            has_live_power = not LIVE_POWER_PROPERTIES.isdisjoint(device.properties)
            if has_live_power and definition is not None and definition.can_control:
                device_uuids.append(device.uuid)
        return device_uuids

    def live_power_available(self, device_uuid: str) -> bool:
        """Return whether a device's live power stream is current."""

        if not self.connected:
            return False
        age = self.client.live_power_age(device_uuid)
        return age is not None and age <= _INSTANT_USAGE_STALE_SECONDS

    async def _async_keep_instant_usage_enabled(self) -> None:
        while True:
            device_uuids = self._instant_usage_devices()
            if device_uuids:
                try:
                    stale_devices = [
                        device_uuid
                        for device_uuid in device_uuids
                        if (age := self.client.live_power_age(device_uuid)) is None
                        or age > _INSTANT_USAGE_STALE_SECONDS
                    ]
                    if stale_devices:
                        # Force a state transition in the controller. Sending
                        # True repeatedly is not sufficient on every firmware
                        # version once its instant-usage stream has stalled.
                        await self.client.async_control_devices(
                            {
                                device_uuid: {"ReportInstantUsage": "False"}
                                for device_uuid in stale_devices
                            }
                        )
                    await self.client.async_control_devices(
                        {
                            device_uuid: {"ReportInstantUsage": "True"}
                            for device_uuid in device_uuids
                        }
                    )
                except NikoError as exc:
                    _LOGGER.warning("Could not enable Niko instant usage: %s", exc)
            await asyncio.sleep(_INSTANT_USAGE_REFRESH_SECONDS)
