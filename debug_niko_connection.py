"""Visual Studio startup script for testing only the Niko protocol layer."""

from __future__ import annotations

import asyncio
import argparse
from collections import defaultdict
import json
from pathlib import Path
from datetime import datetime, timedelta

from custom_components.niko_home_control_local.niko_client import NikoClient
from custom_components.niko_home_control_local.measurements import (
    NikoMeasurementsClient,
    NikoMeasurementsError,
)
from custom_components.niko_home_control_local.models import NikoDevice
from custom_components.niko_home_control_local.discovery import ACCUMULATION_DESCRIPTIONS
from custom_components.niko_home_control_local.history import (
    async_fetch_complete_hourly_history,
)

CONFIG_PATH = Path("debug_config.json")
_MEASUREMENT_TYPES = {"energyhome", "electricitymeter", "watermeter", "centralmeter", "smartplug"}


async def _print_measurement_summary(
    devices: dict[str, NikoDevice], host: str, token: str
) -> None:
    """Probe REST measurements without printing device names or identifiers."""

    rest_client = NikoMeasurementsClient(host=host, token=token)
    groups: dict[tuple[str, str, tuple[str, ...]], int] = defaultdict(int)
    candidates = sorted(
        devices.values(),
        key=lambda device: device.device_type.lower() != "energyhome",
    )
    for device in candidates:
        if device.device_type.lower() not in _MEASUREMENT_TYPES:
            continue
        try:
            measurements = await rest_client.async_get_latest(device.uuid)
            properties = tuple(sorted(measurements))
        except NikoMeasurementsError:
            properties = ("<request-failed>",)
        groups[(device.model or "-", device.device_type or "-", properties)] += 1

    print("REST-meetoverzicht (zonder namen, UUID's of waarden):\n")
    for (model, device_type, properties), count in sorted(groups.items()):
        print(f"{model} / {device_type}: {count} | properties={list(properties) or '-'}")


async def _print_history_probe(
    devices: dict[str, NikoDevice], host: str, token: str
) -> None:
    """Validate aggregated history without printing identifiers or values."""

    rest_client = NikoMeasurementsClient(host=host, token=token)
    now = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
    failures: dict[tuple[str, str, str], int] = defaultdict(int)
    candidates = sorted(
        devices.values(),
        key=lambda device: device.device_type.lower() != "energyhome",
    )
    for device in candidates:
        if device.device_type.lower() != "energyhome":
            continue
        latest = None
        for attempt in range(3):
            try:
                latest = await rest_client.async_get_latest(device.uuid)
                break
            except NikoMeasurementsError:
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
        if latest is None:
            continue
        for property_name in ACCUMULATION_DESCRIPTIONS:
            if property_name not in latest:
                continue
            try:
                history = await async_fetch_complete_hourly_history(
                    rest_client,
                    device.uuid,
                    property_name,
                    now=now,
                    local_timezone=now.tzinfo,
                )
            except NikoMeasurementsError as exc:
                redacted = str(exc).replace(device.uuid, "<uuid>")
                failures[(device.model, device.device_type, redacted)] += 1
                continue
            years = sorted({item.timestamp[:4] for item in history})
            print("Historische REST-probe (zonder UUID's of waarden):")
            print(f"model/type={device.model}/{device.device_type}")
            print(f"property={property_name}")
            print(f"intervallen={len(history)}")
            print(f"periode={years[0] if years else '-'}..{years[-1] if years else '-'}")
            return
    print("Historische REST-probe: geen werkende meetreeks gevonden.")
    for (model, device_type, error), count in sorted(failures.items()):
        print(f"{model}/{device_type}: {count} mislukt ({error})")


async def _print_history_levels_probe(
    devices: dict[str, NikoDevice], host: str, token: str
) -> None:
    """Report retained aggregate levels without identifiers or measurements."""

    rest_client = NikoMeasurementsClient(host=host, token=token, timeout=45.0)
    candidates = sorted(
        devices.values(),
        key=lambda device: device.device_type.lower() != "energyhome",
    )
    for device in candidates:
        if device.device_type.lower() != "energyhome":
            continue
        latest = None
        for attempt in range(3):
            try:
                latest = await rest_client.async_get_latest(device.uuid)
                break
            except NikoMeasurementsError:
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
        if latest is None:
            continue
        property_name = next(
            (name for name in ACCUMULATION_DESCRIPTIONS if name in latest),
            None,
        )
        if property_name is None:
            continue

        now = datetime.now().astimezone()
        next_year = datetime(now.year + 1, 1, 1)
        probes = (
            ("year", "volledig", datetime(2000, 1, 1), next_year),
            (
                "month",
                "volledig",
                datetime(max(2000, now.year - 5), 1, 1),
                next_year,
            ),
            (
                "day",
                "vorig-jaar-proefblok",
                datetime(now.year - 1, 1, 1),
                datetime(now.year - 1, 1, 1) + timedelta(days=90),
            ),
            (
                "day",
                "januari-huidig-jaar",
                datetime(now.year, 1, 1),
                datetime(now.year, 2, 1),
            ),
        )
        print("Historische aggregatieniveaus (zonder UUID's of waarden):")
        print(f"model/type={device.model}/{device.device_type}")
        print(f"property={property_name}")
        for interval, label, start, end in probes:
            try:
                result = await rest_client.async_get_aggregated_history(
                    device.uuid,
                    property_name,
                    interval,
                    start.isoformat(),
                    end.isoformat(),
                )
                timestamps = sorted(item.timestamp for item in result)
                nonzero = sum(item.value != 0 for item in result)
                units = sorted({item.unit for item in result if item.unit})
                print(
                    f"interval={interval} blok={label} "
                    f"aantal={len(timestamps)} niet-nul={nonzero} "
                    f"eenheid={units or '-'} "
                    f"van={timestamps[0] if timestamps else '-'} "
                    f"tot={timestamps[-1] if timestamps else '-'}"
                )
            except NikoMeasurementsError as exc:
                redacted = str(exc).replace(device.uuid, "<uuid>")
                print(f"interval={interval} mislukt={redacted}")
        return
    print("Historische aggregatieniveaus: geen geschikte meetreeks gevonden.")


def _print_capability_summary(devices: dict[str, NikoDevice]) -> None:
    """Print an anonymous summary of device capabilities by model and type."""

    groups: dict[tuple[str, str], list[NikoDevice]] = defaultdict(list)
    for device in devices.values():
        groups[(device.model or "-", device.device_type or "-")].append(device)

    print("Capability-overzicht (zonder namen of UUID's):\n")
    for (model, device_type), grouped_devices in sorted(groups.items()):
        properties = sorted(
            {
                property_name
                for device in grouped_devices
                for property_name in device.properties
            }
        )
        parameters = sorted(
            {
                parameter_name
                for device in grouped_devices
                for parameter_name in device.parameters
            }
        )
        definitions = {
            property_name: definition
            for device in grouped_devices
            for property_name, definition in device.property_definitions.items()
        }
        controllable = sorted(
            name for name, definition in definitions.items() if definition.can_control
        )
        status = sorted(
            name for name, definition in definitions.items() if definition.has_status
        )
        print(
            f"{model} / {device_type}: {len(grouped_devices)} | "
            f"parameters={parameters or '-'} | "
            f"properties={properties or '-'} | "
            f"status={status or '-'} | control={controllable or '-'}"
        )

    identifier_groups: dict[str, list[NikoDevice]] = defaultdict(list)
    for device in devices.values():
        if device.identifier:
            identifier_groups[device.identifier].append(device)
    relationships: dict[tuple[tuple[str, str], ...], int] = defaultdict(int)
    for related_devices in identifier_groups.values():
        if len(related_devices) < 2:
            continue
        relation = tuple(
            sorted({(device.model, device.device_type) for device in related_devices})
        )
        relationships[relation] += 1

    print("\nGedeelde Identifier-relaties:")
    if not relationships:
        print("-")
    for relation, count in sorted(relationships.items()):
        print(f"{relation}: {count}")


async def main(
    *,
    capabilities: bool = False,
    measurements: bool = False,
    notifications: bool = False,
    history: bool = False,
    history_levels: bool = False,
    once: bool = False,
) -> None:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "debug_config.json ontbreekt. Kopieer debug_config.example.json en vul je token in."
        )

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    client = NikoClient(
        host=config["host"],
        port=int(config.get("port", 8884)),
        username=config.get("username", "hobby"),
        password=config["token"],
        client_id="NikoNativeVisualStudioDebug",
    )

    try:
        devices = await client.async_start()
        print(f"Verbonden. devices.list bevat {len(devices)} apparaten.\n")
        if history_levels:
            await _print_history_levels_probe(
                devices, config["host"], config["token"]
            )
        elif history:
            await _print_history_probe(devices, config["host"], config["token"])
        elif notifications:
            items = await client.async_request_notifications()
            groups: dict[tuple[str, str], int] = defaultdict(int)
            for item in items:
                groups[(item.notification_type, item.status or "-")] += 1
            print("Meldingsoverzicht (zonder tekst, tijdstip of UUID):\n")
            if not groups:
                print("-")
            for (notification_type, status), count in sorted(groups.items()):
                print(f"{notification_type} / {status}: {count}")
        elif measurements:
            await _print_measurement_summary(devices, config["host"], config["token"])
        elif capabilities:
            _print_capability_summary(devices)
        else:
            for device in sorted(devices.values(), key=lambda item: item.name.lower()):
                print(
                    f"{device.name} | {device.uuid} | "
                    f"model={device.model} | type={device.device_type}"
                )
        if once:
            return
        print("\nDruk Ctrl+C om de debugverbinding te sluiten.")
        while True:
            await asyncio.sleep(1)
    finally:
        await client.async_stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--history-levels",
        action="store_true",
        help="toon geanonimiseerd welke historische aggregaties beschikbaar zijn",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="controleer geanonimiseerd de historische REST-meetendpoint",
    )
    parser.add_argument(
        "--notifications",
        action="store_true",
        help="toon een geanonimiseerd overzicht van Niko-meldingen",
    )
    parser.add_argument(
        "--measurements",
        action="store_true",
        help="toon een geanonimiseerd overzicht van lokale REST-metingen",
    )
    parser.add_argument(
        "--capabilities",
        action="store_true",
        help="toon alleen een geanonimiseerde capability-samenvatting",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="sluit af zodra devices.list verwerkt is",
    )
    arguments = parser.parse_args()
    try:
        asyncio.run(
            main(
                capabilities=arguments.capabilities,
                measurements=arguments.measurements,
                notifications=arguments.notifications,
                history=arguments.history,
                history_levels=arguments.history_levels,
                once=arguments.once,
            )
        )
    except KeyboardInterrupt:
        pass
