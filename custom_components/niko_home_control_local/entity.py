"""Base entity for Niko Home Control."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .hub import NikoHub
from .models import NikoDevice


class NikoControllerEntity(Entity):
    """Base class for entities representing the connected controller."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: NikoHub, key: str) -> None:
        self.hub = hub
        self._attr_unique_id = f"{hub.identifier}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.hub.identifier)},
            name="Niko Home Control II Controller",
            manufacturer="Niko",
            model="Connected Controller",
            configuration_url=f"https://{self.hub.config.host}",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.hub.add_listener(self._handle_hub_update))

    def _handle_hub_update(self) -> None:
        self.async_write_ha_state()


class NikoDeviceEntity(Entity):
    """Base entity backed by one controllable Niko device object."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        self.hub = hub
        self.device = device
        self._attr_unique_id = device.uuid
        self._attr_name = device.name

    @property
    def available(self) -> bool:
        return self.hub.connected

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.uuid)},
            name=self.device.name,
            manufacturer="Niko",
            model=self.device.model or self.device.device_type,
            suggested_area=self.device.parameters.get("LocationName"),
            via_device=(DOMAIN, self.hub.identifier),
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.hub.add_listener(self._handle_hub_update))

    def _handle_hub_update(self) -> None:
        self.async_write_ha_state()
