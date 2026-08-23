from __future__ import annotations

import asyncio
import json
import ssl
from types import SimpleNamespace

import pytest

from paho.mqtt import MQTTException
import paho.mqtt.client as mqtt

from custom_components.niko_home_control_local.niko_client import (
    NikoCannotConnect,
    NikoClient,
    NikoProtocolError,
    _create_unverified_tls_context,
)
from custom_components.niko_home_control_local.models import (
    NikoDevice,
    PropertyDefinition,
)


def _client() -> NikoClient:
    return NikoClient(
        host="controller.local",
        port=8884,
        username="hobby",
        password="secret",
        client_id="test-client",
    )


def test_tls_context_does_not_require_system_ca_certificates() -> None:
    context = _create_unverified_tls_context()

    assert context.check_hostname is False
    assert context.verify_mode == ssl.CERT_NONE


def test_connect_timeout_stops_client(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_test() -> None:
        client = _client()
        monkeypatch.setattr(client, "_start_network_loop", lambda: None)
        monkeypatch.setattr(client, "_disconnect_blocking", lambda: None)

        with pytest.raises(NikoCannotConnect, match="Timeout connecting"):
            await client.async_start(connect_timeout=0.01)

        assert client._started is False
        assert client.connected is False

    asyncio.run(run_test())


def test_network_loop_uses_paho_connect_async_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client()
    connect_calls: list[tuple[str, int, int]] = []
    monkeypatch.setattr(
        client._client,
        "connect_async",
        lambda host, port, keepalive: connect_calls.append((host, port, keepalive)),
    )
    monkeypatch.setattr(
        client._client, "loop_start", lambda: mqtt.MQTT_ERR_SUCCESS
    )

    client._start_network_loop()

    assert connect_calls == [("controller.local", 8884, 60)]


def test_network_loop_reports_start_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    monkeypatch.setattr(client._client, "connect_async", lambda *args, **kwargs: None)
    monkeypatch.setattr(client._client, "loop_start", lambda: mqtt.MQTT_ERR_INVAL)

    with pytest.raises(MQTTException, match="loop_start failed"):
        client._start_network_loop()


def test_non_object_json_is_reported_without_crashing_callback() -> None:
    async def run_test() -> None:
        client = _client()
        client._loop = asyncio.get_running_loop()
        message = SimpleNamespace(
            topic="hobby/control/devices/evt",
            payload=b"[]",
        )

        client._on_message(None, None, message)
        await asyncio.sleep(0)

        assert client.last_error == (
            "Invalid payload on hobby/control/devices/evt: expected a JSON object"
        )

    asyncio.run(run_test())


def test_disconnect_fails_pending_connection_and_device_requests() -> None:
    async def run_test() -> None:
        client = _client()
        loop = asyncio.get_running_loop()
        client.connected = True
        client._connect_future = loop.create_future()
        client._devices_future = loop.create_future()

        client._handle_disconnected("Disconnected: connection lost")

        assert client.connected is False
        for future in (client._connect_future, client._devices_future):
            with pytest.raises(NikoCannotConnect, match="connection lost"):
                await future

    asyncio.run(run_test())


def test_control_device_publishes_official_devices_control_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_test() -> None:
        client = _client()
        client.connected = True
        client.devices["device-1"] = NikoDevice(
            uuid="device-1",
            name="Test light",
            property_definitions={
                "Status": PropertyDefinition(name="Status", can_control=True)
            },
        )
        published: list[tuple[str, str, int, bool]] = []

        def publish(topic: str, payload: str, qos: int, retain: bool) -> object:
            published.append((topic, payload, qos, retain))
            return SimpleNamespace(rc=mqtt.MQTT_ERR_SUCCESS)

        monkeypatch.setattr(client._client, "publish", publish)

        await client.async_control_device("device-1", {"Status": "On"})

        assert len(published) == 1
        topic, raw_payload, qos, retain = published[0]
        assert topic == "hobby/control/devices/cmd"
        assert qos == 0
        assert retain is False
        assert json.loads(raw_payload) == {
            "Method": "devices.control",
            "Params": [
                {
                    "Devices": [
                        {
                            "Uuid": "device-1",
                            "Properties": [{"Status": "On"}],
                        }
                    ]
                }
            ],
        }

    asyncio.run(run_test())


def test_control_device_rejects_undeclared_property() -> None:
    async def run_test() -> None:
        client = _client()
        client.connected = True
        client.devices["device-1"] = NikoDevice(uuid="device-1", name="Test")

        with pytest.raises(NikoProtocolError, match="cannot be controlled"):
            await client.async_control_device("device-1", {"Status": "On"})

    asyncio.run(run_test())


def test_control_devices_batches_multiple_devices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_test() -> None:
        client = _client()
        client.connected = True
        for uuid in ("plug-1", "energy-1"):
            client.devices[uuid] = NikoDevice(
                uuid=uuid,
                name=uuid,
                property_definitions={
                    "ReportInstantUsage": PropertyDefinition(
                        name="ReportInstantUsage", can_control=True
                    )
                },
            )
        published: list[str] = []

        def publish(topic: str, payload: str, qos: int, retain: bool) -> object:
            published.append(payload)
            return SimpleNamespace(rc=mqtt.MQTT_ERR_SUCCESS)

        monkeypatch.setattr(client._client, "publish", publish)

        await client.async_control_devices(
            {
                "plug-1": {"ReportInstantUsage": "True"},
                "energy-1": {"ReportInstantUsage": "True"},
            }
        )

        assert json.loads(published[0])["Params"][0]["Devices"] == [
            {
                "Uuid": "plug-1",
                "Properties": [{"ReportInstantUsage": "True"}],
            },
            {
                "Uuid": "energy-1",
                "Properties": [{"ReportInstantUsage": "True"}],
            },
        ]

    asyncio.run(run_test())
