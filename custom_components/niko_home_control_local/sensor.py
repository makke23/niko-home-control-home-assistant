"""Sensors for Niko Home Control."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .discovery import (
    NikoAccumulationDescription,
    NikoEnumSensorDescription,
    NikoSensorDescription,
    discover_accumulated_measurements,
    discover_enum_sensors,
    discover_sensors,
)
from .auth import token_expiration
from .entity import NikoControllerEntity, NikoDeviceEntity
from .hub import HistoricalImportRecord, NikoHub
from .history import (
    async_fetch_complete_hourly_history,
    build_hourly_statistics,
)
from .measurements import IntervalAccumulator, NikoMeasurementsError
from .models import NikoDevice

_LOGGER = logging.getLogger(__name__)
_HISTORY_IMPORT_SCHEMA_VERSION = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    accumulated = discover_accumulated_measurements(
        hub.client.devices, hub.measurements
    )
    hub.set_history_import_expected(len(accumulated))
    async_add_entities(
        [NikoDeviceCountSensor(hub)]
        + [NikoTokenExpirySensor(hub)]
        + [NikoHistoryImportSensor(hub)]
        + [
            NikoPropertySensor(hub, device, description)
            for device, description in discover_sensors(hub.client.devices)
        ]
        + [
            NikoEnumPropertySensor(hub, device, description)
            for device, description in discover_enum_sensors(hub.client.devices)
        ]
        + [
            NikoAccumulatedMeasurementSensor(hub, device, description)
            for device, description in accumulated
        ]
    )
    del hass


class NikoDeviceCountSensor(NikoControllerEntity, SensorEntity):
    """Number of devices returned by the controller."""

    _attr_translation_key = "device_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:devices"

    def __init__(self, hub: NikoHub) -> None:
        super().__init__(hub, "device_count")

    @property
    def native_value(self) -> int:
        return self.hub.device_count


class NikoTokenExpirySensor(NikoControllerEntity, SensorEntity):
    """Expiry timestamp of the locally configured Hobby API token."""

    _attr_translation_key = "token_expiry"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:key-clock"

    def __init__(self, hub: NikoHub) -> None:
        super().__init__(hub, "token_expiry")
        self._expiration = token_expiration(hub.config.token)

    @property
    def native_value(self) -> datetime | None:
        return self._expiration

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        if self._expiration is None:
            return {}
        remaining = self._expiration - datetime.now(timezone.utc)
        return {"days_remaining": max(0, remaining.days)}


class NikoHistoryImportSensor(NikoControllerEntity, SensorEntity):
    """Progress and result of the pre-installation history import."""

    _attr_translation_key = "history_import"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "pending",
        "running",
        "completed",
        "partial",
        "failed",
        "not_applicable",
    ]
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:database-import"

    def __init__(self, hub: NikoHub) -> None:
        super().__init__(hub, "history_import")

    @property
    def native_value(self) -> str:
        return self.hub.history_import_status

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None]:
        records = list(self.hub.history_import_records.values())
        starts = [record.earliest for record in records if record.earliest]
        ends = [record.latest for record in records if record.latest]
        return {
            "series_expected": self.hub.history_import_expected,
            "series_processed": len(records),
            "measurements_imported": sum(
                record.measurement_count for record in records
            ),
            "earliest_imported": min(starts) if starts else None,
            "latest_imported": max(ends) if ends else None,
            "errors": sum(record.status == "error" for record in records),
        }


class NikoPropertySensor(NikoDeviceEntity, SensorEntity):
    """A numeric Niko device property."""

    def __init__(
        self,
        hub: NikoHub,
        device: NikoDevice,
        description: NikoSensorDescription,
    ) -> None:
        super().__init__(hub, device)
        self.description = description
        self._attr_unique_id = f"{device.uuid}_{description.property_name}"
        self._attr_name = f"{device.name} {description.name}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = SensorDeviceClass(description.device_class)
        self._attr_state_class = SensorStateClass(description.state_class)

    @property
    def native_value(self) -> int | float | None:
        try:
            value = float(self.device.properties[self.description.property_name])
        except (KeyError, TypeError, ValueError):
            return None
        return int(value) if value.is_integer() else value


class NikoEnumPropertySensor(NikoDeviceEntity, SensorEntity):
    """A textual Niko device status represented as an enum sensor."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self,
        hub: NikoHub,
        device: NikoDevice,
        description: NikoEnumSensorDescription,
    ) -> None:
        super().__init__(hub, device)
        self.description = description
        self._attr_unique_id = f"{device.uuid}_{description.property_name}"
        self._attr_name = f"{device.name} {description.name}"
        self._attr_options = list(description.options)

    @property
    def native_value(self) -> str | None:
        value = self.device.properties.get(self.description.property_name)
        if value is None:
            return None
        text = str(value)
        return text if text in self._attr_options else None


class NikoAccumulatedMeasurementSensor(
    NikoDeviceEntity, SensorEntity, RestoreEntity
):
    """A persisted total built from timestamped Niko interval measurements."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        hub: NikoHub,
        device: NikoDevice,
        description: NikoAccumulationDescription,
    ) -> None:
        super().__init__(hub, device)
        self.description = description
        self._accumulator = IntervalAccumulator()
        self._history_task: asyncio.Task[None] | None = None
        self._historical_import_completed = False
        self._historical_measurement_count = 0
        self._historical_import_schema = 0
        self._historical_earliest: str | None = None
        self._historical_latest: str | None = None
        self._attr_unique_id = f"{device.uuid}_{description.property_name}_total"
        self._attr_name = f"{device.name} {description.name}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = SensorDeviceClass(description.device_class)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._accumulator.total = float(last_state.state)
            except (TypeError, ValueError):
                self._accumulator.total = None
            timestamp = last_state.attributes.get("last_measurement_timestamp")
            if isinstance(timestamp, str):
                self._accumulator.last_timestamp = timestamp
            self._historical_import_completed = bool(
                last_state.attributes.get("historical_import_completed", False)
            )
            try:
                self._historical_measurement_count = int(
                    last_state.attributes.get("historical_measurement_count", 0)
                )
            except (TypeError, ValueError):
                self._historical_measurement_count = 0
            try:
                self._historical_import_schema = int(
                    last_state.attributes.get("historical_import_schema", 0)
                )
            except (TypeError, ValueError):
                self._historical_import_schema = 0
            earliest = last_state.attributes.get("historical_earliest")
            latest = last_state.attributes.get("historical_latest")
            self._historical_earliest = earliest if isinstance(earliest, str) else None
            self._historical_latest = latest if isinstance(latest, str) else None

        if (
            self._historical_import_completed
            and self._historical_import_schema >= _HISTORY_IMPORT_SCHEMA_VERSION
        ):
            self.hub.update_history_import(
                self._history_key,
                self._history_record("completed"),
            )
            await self._async_backfill_missing_intervals()
            self._consume_latest_interval()
            return

        # Do not publish a small provisional total before the first full import.
        # Recorder would interpret the subsequent historical total as a meter
        # reset and create large negative/positive changes in period charts.
        self._historical_import_completed = False
        self._history_task = self.hass.async_create_task(
            self._async_import_complete_history(),
            f"niko_history_import_{self.unique_id}",
        )

    async def async_will_remove_from_hass(self) -> None:
        """Cancel a running import when the entity is removed."""

        if self._history_task is not None:
            self._history_task.cancel()
            try:
                await self._history_task
            except asyncio.CancelledError:
                pass
            self._history_task = None
        await super().async_will_remove_from_hass()

    @property
    def _history_key(self) -> str:
        return f"{self.device.uuid}:{self.description.property_name}"

    def _history_record(
        self, status: str, error: str | None = None
    ) -> HistoricalImportRecord:
        return HistoricalImportRecord(
            status=status,
            measurement_count=self._historical_measurement_count,
            earliest=self._historical_earliest,
            latest=self._historical_latest,
            error=error,
        )

    async def _async_import_complete_history(self) -> None:
        """Fetch all retained Niko history and import hourly statistics."""

        self.hub.update_history_import(
            self._history_key, self._history_record("running")
        )
        try:
            local_timezone = (
                dt_util.get_time_zone(self.hass.config.time_zone) or timezone.utc
            )
            async with self.hub.history_import_semaphore:
                measurements = await async_fetch_complete_hourly_history(
                    self.hub.measurements_client,
                    self.device.uuid,
                    self.description.property_name,
                    now=datetime.now(timezone.utc),
                    local_timezone=local_timezone,
                )
            statistics = build_hourly_statistics(
                measurements,
                divisor=self.description.divisor,
                local_timezone=local_timezone,
            )
            if statistics:
                metadata: StatisticMetaData = {
                    "mean_type": StatisticMeanType.NONE,
                    "has_sum": True,
                    "name": self.name,
                    "source": "recorder",
                    "statistic_id": self.entity_id,
                    "unit_class": (
                        "energy"
                        if self.description.device_class == "energy"
                        else "volume"
                    ),
                    "unit_of_measurement": self.description.unit,
                }
                statistic_data: list[StatisticData] = [
                    {
                        "start": statistic.start,
                        "state": statistic.state,
                        "sum": statistic.sum,
                    }
                    for statistic in statistics
                ]
                async_import_statistics(self.hass, metadata, statistic_data)
                self._accumulator.total = statistics[-1].state
                self._accumulator.last_timestamp = measurements[-1].timestamp
                self._consume_latest_interval()
                self._historical_earliest = statistics[0].start.isoformat()
                self._historical_latest = statistics[-1].start.isoformat()

            self._historical_measurement_count = len(statistics)
            self._historical_import_completed = True
            self._historical_import_schema = _HISTORY_IMPORT_SCHEMA_VERSION
            self.hub.update_history_import(
                self._history_key, self._history_record("completed")
            )
            self.async_write_ha_state()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - HA/network boundary
            _LOGGER.warning(
                "Could not import historical Niko measurements for %s: %s",
                self.description.property_name,
                exc,
            )
            self.hub.update_history_import(
                self._history_key,
                self._history_record("error", type(exc).__name__),
            )

    async def _async_backfill_missing_intervals(self) -> None:
        """Recover intervals missed while Home Assistant was offline."""

        start = self._accumulator.last_timestamp
        if start is None:
            return
        interval_end = datetime.now().astimezone().replace(
            second=0, microsecond=0
        )
        interval_end = interval_end.replace(
            minute=(interval_end.minute // 15) * 15,
            tzinfo=None,
        )
        try:
            measurements = await self.hub.measurements_client.async_get_history(
                self.device.uuid,
                self.description.property_name,
                start,
                interval_end.isoformat(),
            )
        except NikoMeasurementsError:
            return
        self._accumulator.consume_many(
            measurements, divisor=self.description.divisor
        )

    def _handle_hub_update(self) -> None:
        self._consume_latest_interval()
        super()._handle_hub_update()

    def _consume_latest_interval(self) -> None:
        measurement = self.hub.measurements.get(self.device.uuid, {}).get(
            self.description.property_name
        )
        if measurement is None:
            return
        self._accumulator.consume(measurement, divisor=self.description.divisor)

    @property
    def native_value(self) -> float | None:
        total = self._accumulator.total
        return None if total is None else round(total, 6)

    @property
    def extra_state_attributes(self) -> dict[str, str | int | bool]:
        attributes: dict[str, str | int | bool] = {
            "historical_import_completed": self._historical_import_completed,
            "historical_measurement_count": self._historical_measurement_count,
            "historical_import_schema": self._historical_import_schema,
        }
        if self._accumulator.last_timestamp is not None:
            attributes["last_measurement_timestamp"] = (
                self._accumulator.last_timestamp
            )
        if self._historical_earliest is not None:
            attributes["historical_earliest"] = self._historical_earliest
        if self._historical_latest is not None:
            attributes["historical_latest"] = self._historical_latest
        return attributes
