"""Audio control for Niko Home Control."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .discovery import can_control, discover_audio_actions
from .entity import NikoDeviceEntity
from .hub import NikoHub
from .models import NikoDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikoHub],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    del hass
    async_add_entities(
        NikoAudioPlayer(entry.runtime_data, device)
        for device in discover_audio_actions(entry.runtime_data.client.devices)
    )


class NikoAudioPlayer(NikoDeviceEntity, MediaPlayerEntity):
    """A Bose or Sonos action controlled by Niko."""

    def __init__(self, hub: NikoHub, device: NikoDevice) -> None:
        super().__init__(hub, device)
        features = MediaPlayerEntityFeature(0)
        if can_control(device, "Status"):
            features |= MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
        if can_control(device, "Playback"):
            features |= MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE
        if can_control(device, "Volume"):
            features |= MediaPlayerEntityFeature.VOLUME_SET
        if can_control(device, "Muted"):
            features |= MediaPlayerEntityFeature.VOLUME_MUTE
        self._attr_supported_features = features

    @property
    def state(self) -> MediaPlayerState:
        if str(self.device.properties.get("Status", "On")).lower() == "off":
            return MediaPlayerState.OFF
        return {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "buffering": MediaPlayerState.BUFFERING,
        }.get(str(self.device.properties.get("Playback", "Paused")).lower(), MediaPlayerState.IDLE)

    @property
    def volume_level(self) -> float | None:
        try:
            return max(0.0, min(1.0, float(self.device.properties["Volume"]) / 100))
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def is_volume_muted(self) -> bool:
        return str(self.device.properties.get("Muted", "False")).lower() in {"true", "1", "on"}

    @property
    def media_title(self) -> str | None:
        title = self.device.properties.get("Title")
        return str(title) if title else None

    async def async_turn_on(self) -> None:
        await self.hub.async_control_device(self.device.uuid, {"Status": "On"})

    async def async_turn_off(self) -> None:
        await self.hub.async_control_device(self.device.uuid, {"Status": "Off"})

    async def async_media_play(self) -> None:
        await self.hub.async_control_device(self.device.uuid, {"Playback": "Playing"})

    async def async_media_pause(self) -> None:
        await self.hub.async_control_device(self.device.uuid, {"Playback": "Paused"})

    async def async_set_volume_level(self, volume: float) -> None:
        await self.hub.async_control_device(
            self.device.uuid, {"Volume": str(round(max(0.0, min(1.0, volume)) * 100))}
        )

    async def async_mute_volume(self, mute: bool) -> None:
        await self.hub.async_control_device(self.device.uuid, {"Muted": str(mute)})
