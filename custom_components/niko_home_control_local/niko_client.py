"""Thread-safe asynchronous wrapper around Niko's local MQTT Hobby API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import logging
import ssl
import time
from typing import Any

from paho.mqtt import MQTTException
import paho.mqtt.client as mqtt

from .const import LIVE_POWER_PROPERTIES
from .models import NikoDevice, NikoNotification, parse_devices_list, parse_notifications

_LOGGER = logging.getLogger(__name__)

_DEVICE_COMMAND_TOPIC = "hobby/control/devices/cmd"
_NOTIFICATION_COMMAND_TOPIC = "hobby/notification/cmd"
_SUBSCRIBE_TOPICS = (
    "hobby/control/devices/evt",
    "hobby/control/devices/rsp",
    "hobby/control/devices/err",
    "hobby/system/evt",
    "hobby/notification/evt",
    "hobby/notification/rsp",
    "hobby/notification/err",
)


def _create_unverified_tls_context() -> ssl.SSLContext:
    """Create the controller TLS context without loading system CA certificates."""

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


class NikoError(Exception):
    """Base exception for Niko client errors."""


class NikoCannotConnect(NikoError):
    """Raised when the controller cannot be reached."""


class NikoAuthenticationError(NikoError):
    """Raised when the controller rejects the credentials."""


class NikoProtocolError(NikoError):
    """Raised when the controller sends an invalid response."""


class NikoClient:
    """Manage one Niko MQTT connection without blocking Home Assistant's event loop."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        client_id: str,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id

        self.devices: dict[str, NikoDevice] = {}
        self.notifications: dict[str, NikoNotification] = {}
        self._last_live_power_update: dict[str, float] = {}
        self.connected = False
        self.last_error: str | None = None

        self._loop: asyncio.AbstractEventLoop | None = None
        self._connect_future: asyncio.Future[None] | None = None
        self._devices_future: asyncio.Future[dict[str, NikoDevice]] | None = None
        self._notifications_future: asyncio.Future[list[NikoNotification]] | None = None
        self._listeners: set[Callable[[], None]] = set()
        self._notification_listeners: set[Callable[[NikoNotification], None]] = set()
        self._stopping = False
        self._started = False
        self._refresh_task: asyncio.Task[None] | None = None

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        self._client.username_pw_set(username, password)
        self._client.tls_set_context(_create_unverified_tls_context())
        self._client.tls_insecure_set(True)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def live_power_age(self, device_uuid: str) -> float | None:
        """Return seconds since a live power value was received."""

        updated_at = self._last_live_power_update.get(device_uuid)
        if updated_at is None:
            return None
        return max(0.0, time.monotonic() - updated_at)

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback executed in Home Assistant's event loop."""

        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    def notify_listeners(self) -> None:
        """Notify entities after data from an auxiliary local API changes."""

        self._notify_listeners()

    def add_notification_listener(
        self, listener: Callable[[NikoNotification], None]
    ) -> Callable[[], None]:
        """Register a callback for newly raised Niko notifications."""

        self._notification_listeners.add(listener)

        def remove_listener() -> None:
            self._notification_listeners.discard(listener)

        return remove_listener

    async def async_start(
        self,
        *,
        connect_timeout: float = 15.0,
        device_timeout: float = 15.0,
    ) -> dict[str, NikoDevice]:
        """Connect, subscribe and obtain the initial complete device snapshot."""

        if self._started:
            return self.devices

        self._started = True
        self._stopping = False
        self._loop = asyncio.get_running_loop()
        self._connect_future = self._loop.create_future()

        try:
            self._start_network_loop()
            await asyncio.wait_for(self._connect_future, timeout=connect_timeout)
            return await self.async_request_devices(timeout=device_timeout)
        except TimeoutError as exc:
            await self.async_stop()
            raise NikoCannotConnect(
                f"Timeout connecting to Niko controller {self.host}:{self.port}"
            ) from exc
        except (OSError, MQTTException) as exc:
            await self.async_stop()
            raise NikoCannotConnect(
                f"Cannot connect to Niko controller {self.host}:{self.port}: {exc}"
            ) from exc
        except Exception:
            await self.async_stop()
            raise

    async def async_stop(self) -> None:
        """Stop the network loop and release all callbacks."""

        if not self._started:
            return

        self._stopping = True
        self._started = False
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            self._refresh_task = None
        try:
            await asyncio.to_thread(self._disconnect_blocking)
        finally:
            self.connected = False
            for future in (
                self._connect_future,
                self._devices_future,
                self._notifications_future,
            ):
                if future is not None and not future.done():
                    future.cancel()
            self._connect_future = None
            self._devices_future = None
            self._notifications_future = None
            self._notify_listeners()

    async def async_request_devices(
        self, *, timeout: float = 15.0
    ) -> dict[str, NikoDevice]:
        """Request and await a complete devices.list response."""

        if not self.connected or self._loop is None:
            raise NikoCannotConnect("Niko MQTT is not connected")

        if self._devices_future is not None and not self._devices_future.done():
            self._devices_future.cancel()

        self._devices_future = self._loop.create_future()
        result = self._client.publish(
            _DEVICE_COMMAND_TOPIC,
            json.dumps({"Method": "devices.list"}),
            qos=0,
            retain=False,
        )
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise NikoCannotConnect(f"devices.list publish failed: rc={result.rc}")

        try:
            return await asyncio.wait_for(self._devices_future, timeout=timeout)
        except TimeoutError as exc:
            raise NikoCannotConnect("Niko did not answer devices.list in time") from exc

    async def async_control_device(
        self, device_uuid: str, properties: dict[str, Any]
    ) -> None:
        """Set one or more controllable properties on a Niko device."""

        await self.async_control_devices({device_uuid: properties})

    async def async_request_notifications(
        self, *, timeout: float = 5.0
    ) -> list[NikoNotification]:
        """Request and await the controller's retained notification list."""

        if not self.connected or self._loop is None:
            raise NikoCannotConnect("Niko MQTT is not connected")
        if self._notifications_future is not None and not self._notifications_future.done():
            self._notifications_future.cancel()
        self._notifications_future = self._loop.create_future()
        result = self._client.publish(
            _NOTIFICATION_COMMAND_TOPIC,
            json.dumps({"Method": "notifications.list"}),
            qos=0,
            retain=False,
        )
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise NikoCannotConnect(f"notifications.list publish failed: rc={result.rc}")
        try:
            return await asyncio.wait_for(self._notifications_future, timeout=timeout)
        except TimeoutError as exc:
            raise NikoCannotConnect("Niko did not answer notifications.list in time") from exc

    async def async_control_devices(
        self, changes: dict[str, dict[str, Any]]
    ) -> None:
        """Set controllable properties on one or more Niko devices."""

        if not self.connected:
            raise NikoCannotConnect("Niko MQTT is not connected")
        if not changes:
            raise NikoProtocolError("No Niko devices supplied")

        raw_devices: list[dict[str, Any]] = []
        for device_uuid, properties in changes.items():
            device = self.devices.get(device_uuid)
            if device is None:
                raise NikoProtocolError(f"Unknown Niko device: {device_uuid}")
            if not properties:
                raise NikoProtocolError("No Niko device properties supplied")

            for property_name in properties:
                definition = device.property_definitions.get(property_name)
                if definition is None or not definition.can_control:
                    raise NikoProtocolError(
                        f"Property {property_name!r} cannot be controlled on "
                        f"{device.name}"
                    )
            raw_devices.append(
                {
                    "Uuid": device_uuid,
                    "Properties": [
                        {name: value} for name, value in properties.items()
                    ],
                }
            )

        payload = {
            "Method": "devices.control",
            "Params": [{"Devices": raw_devices}],
        }
        result = self._client.publish(
            _DEVICE_COMMAND_TOPIC,
            json.dumps(payload),
            qos=0,
            retain=False,
        )
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise NikoCannotConnect(f"devices.control publish failed: rc={result.rc}")

    def _start_network_loop(self) -> None:
        """Start a non-blocking connection attempt in Paho's network thread."""

        self._client.connect_async(self.host, self.port, keepalive=60)

        result = self._client.loop_start()
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MQTTException(f"loop_start failed: rc={result}")

    def _disconnect_blocking(self) -> None:
        try:
            self._client.disconnect()
        finally:
            self._client.loop_stop()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        connect_flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del userdata, connect_flags, properties
        if reason_code.is_failure:
            reason = str(reason_code)
            if reason in {"Bad user name or password", "Not authorized"}:
                error: Exception = NikoAuthenticationError(
                    f"Niko MQTT authentication failed: {reason}"
                )
            else:
                error = NikoCannotConnect(f"Niko MQTT connection failed: {reason}")
            self._schedule(self._handle_connect_failure, error)
            return

        for topic in _SUBSCRIBE_TOPICS:
            result, _message_id = client.subscribe(topic)
            if result != mqtt.MQTT_ERR_SUCCESS:
                self._schedule(
                    self._handle_connect_failure,
                    NikoCannotConnect(f"Niko MQTT subscribe failed: rc={result}"),
                )
                return

        self._schedule(self._handle_connected)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del client, userdata, disconnect_flags, properties
        detail = None
        if not self._stopping:
            detail = f"Disconnected: {reason_code}"
        self._schedule(self._handle_disconnected, detail)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        del client, userdata
        try:
            payload = json.loads(message.payload.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._schedule(
                self._set_error, f"Invalid JSON on {message.topic}: {exc}"
            )
            return

        if not isinstance(payload, dict):
            self._schedule(
                self._set_error,
                f"Invalid payload on {message.topic}: expected a JSON object",
            )
            return

        if message.topic.endswith("/err"):
            self._schedule(
                self._set_error, str(payload.get("ErrMessage") or payload)
            )
            return

        method = payload.get("Method")
        if method == "devices.list":
            try:
                devices = parse_devices_list(payload)
            except (TypeError, ValueError) as exc:
                self._schedule_devices_result(
                    error=NikoProtocolError(f"Invalid devices.list payload: {exc}")
                )
                return
            self._schedule_devices_result(devices=devices)
            return

        if method == "devices.status":
            self._schedule_status_payload(payload)
            return

        if method in {"notification.list", "notifications.list"}:
            self._schedule_notifications_payload(payload, raised=False)
            return

        if method == "notifications.raised":
            self._schedule_notifications_payload(payload, raised=True)

    def _schedule(self, callback: Callable[..., None], *args: Any) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(callback, *args)

    def _handle_connected(self) -> None:
        initial_connect = (
            self._connect_future is not None and not self._connect_future.done()
        )
        self.connected = True
        self.last_error = None
        if initial_connect:
            self._connect_future.set_result(None)
        elif self._started and not self._stopping:
            if self._refresh_task is None or self._refresh_task.done():
                self._refresh_task = asyncio.create_task(
                    self._async_refresh_after_reconnect(),
                    name="niko_devices_refresh_after_reconnect",
                )
        self._notify_listeners()

    def _handle_connect_failure(self, error: Exception) -> None:
        self.connected = False
        self.last_error = str(error)
        future = self._connect_future
        if future is not None and not future.done():
            future.set_exception(error)
        self._notify_listeners()

    def _handle_disconnected(self, detail: str | None) -> None:
        self.connected = False
        if detail:
            self.last_error = detail
            error = NikoCannotConnect(detail)
            for future in (
                self._connect_future,
                self._devices_future,
                self._notifications_future,
            ):
                if future is not None and not future.done():
                    future.set_exception(error)
        self._notify_listeners()

    def _set_error(self, detail: str) -> None:
        self.last_error = detail
        _LOGGER.warning("Niko controller error: %s", detail)
        self._notify_listeners()

    async def _async_refresh_after_reconnect(self) -> None:
        try:
            await self.async_request_devices()
        except (NikoError, asyncio.CancelledError):
            if not self._stopping:
                _LOGGER.warning("Could not refresh Niko devices after reconnect")

    def _schedule_devices_result(
        self,
        *,
        devices: dict[str, NikoDevice] | None = None,
        error: Exception | None = None,
    ) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._finish_devices, devices, error)

    def _finish_devices(
        self,
        devices: dict[str, NikoDevice] | None,
        error: Exception | None,
    ) -> None:
        future = self._devices_future
        if future is None or future.done():
            return
        if error is not None:
            future.set_exception(error)
            return
        received = devices or {}
        # Keep object identity stable. Home Assistant entities retain the
        # NikoDevice object created during setup; replacing it after an MQTT
        # reconnect would leave those entities permanently frozen.
        for uuid, fresh in received.items():
            current = self.devices.get(uuid)
            if current is None:
                self.devices[uuid] = fresh
                if not LIVE_POWER_PROPERTIES.isdisjoint(fresh.properties):
                    self._last_live_power_update[uuid] = time.monotonic()
                continue
            current.name = fresh.name
            current.model = fresh.model
            current.device_type = fresh.device_type
            current.technology = fresh.technology
            current.identifier = fresh.identifier
            current.parameters.clear()
            current.parameters.update(fresh.parameters)
            current.properties.clear()
            current.properties.update(fresh.properties)
            current.property_definitions.clear()
            current.property_definitions.update(fresh.property_definitions)
            current.raw = fresh.raw
        for uuid in set(self.devices) - set(received):
            self.devices.pop(uuid, None)
            self._last_live_power_update.pop(uuid, None)
        future.set_result(self.devices)
        self._notify_listeners()

    def _schedule_status_payload(self, payload: dict[str, Any]) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._apply_status_payload, payload)

    def _apply_status_payload(self, payload: dict[str, Any]) -> None:
        for param in payload.get("Params", []) or []:
            if not isinstance(param, dict):
                continue
            for raw_device in param.get("Devices", []) or []:
                if not isinstance(raw_device, dict):
                    continue
                device = self.devices.get(str(raw_device.get("Uuid") or ""))
                if device is None:
                    continue
                has_live_power = False
                for raw_property in raw_device.get("Properties", []) or []:
                    if isinstance(raw_property, dict):
                        device.properties.update(raw_property)
                        if not LIVE_POWER_PROPERTIES.isdisjoint(raw_property):
                            has_live_power = True
                if has_live_power:
                    self._last_live_power_update[device.uuid] = time.monotonic()
        self._notify_listeners()

    def _schedule_notify(self) -> None:
        self._schedule(self._notify_listeners)

    def _schedule_notifications_payload(
        self, payload: dict[str, Any], *, raised: bool
    ) -> None:
        self._schedule(self._apply_notifications_payload, payload, raised)

    def _apply_notifications_payload(
        self, payload: dict[str, Any], raised: bool
    ) -> None:
        parsed = parse_notifications(payload)
        for notification in parsed:
            self.notifications[notification.uuid] = notification
        if not raised:
            future = self._notifications_future
            if future is not None and not future.done():
                future.set_result(parsed)
            return
        for notification in parsed:
            for listener in tuple(self._notification_listeners):
                try:
                    listener(notification)
                except Exception:  # pragma: no cover - defensive boundary
                    _LOGGER.exception("Niko notification listener failed")

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            try:
                listener()
            except Exception:  # pragma: no cover - defensive integration boundary
                _LOGGER.exception("Niko listener failed")
