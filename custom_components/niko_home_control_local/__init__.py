"""Native Home Assistant integration for Niko Home Control.

Developed by Maarten Moortgat.

Home Assistant-specific imports are deferred until Home Assistant calls the
integration lifecycle functions. This keeps the reusable Niko protocol client
importable in a normal Visual Studio Python environment.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .hub import NikoHub

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up shared integration resources."""

    from .frontend import async_register_dashboard_strategy

    await async_register_dashboard_strategy(hass)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration after its credentials are updated."""

    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry[NikoHub]
) -> bool:
    """Set up Niko Home Control from a config entry."""

    from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, Platform
    from homeassistant.exceptions import ConfigEntryNotReady

    from .const import CONF_TOKEN, DEFAULT_CLIENT_ID_PREFIX
    from .hub import NikoHub, NikoHubConfig
    from .niko_client import NikoCannotConnect, NikoError

    hub = NikoHub(
        NikoHubConfig(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            username=entry.data[CONF_USERNAME],
            token=entry.data[CONF_TOKEN],
            client_id=f"{DEFAULT_CLIENT_ID_PREFIX}-{entry.entry_id[:8]}",
        )
    )

    try:
        await hub.async_setup()
    except NikoCannotConnect as exc:
        raise ConfigEntryNotReady(str(exc)) from exc
    except NikoError as exc:
        _LOGGER.error("Cannot set up Niko Home Control: %s", exc)
        return False

    old_default_title = f"Niko Home Control ({entry.data[CONF_HOST]})"
    if entry.title == old_default_title:
        hass.config_entries.async_update_entry(
            entry,
            title=f"Niko Home Control II ({entry.data[CONF_HOST]})",
        )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    entry.runtime_data = hub
    await hass.config_entries.async_forward_entry_setups(
        entry,
        [
            Platform.BINARY_SENSOR,
            Platform.BUTTON,
            Platform.CLIMATE,
            Platform.COVER,
            Platform.EVENT,
            Platform.FAN,
            Platform.LIGHT,
            Platform.MEDIA_PLAYER,
            Platform.SELECT,
            Platform.SCENE,
            Platform.SENSOR,
            Platform.SWITCH,
            Platform.WATER_HEATER,
        ],
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry[NikoHub]
) -> bool:
    """Unload the integration and stop its MQTT network thread."""

    from homeassistant.const import Platform

    unloaded = await hass.config_entries.async_unload_platforms(
        entry,
        [
            Platform.BINARY_SENSOR,
            Platform.BUTTON,
            Platform.CLIMATE,
            Platform.COVER,
            Platform.EVENT,
            Platform.FAN,
            Platform.LIGHT,
            Platform.MEDIA_PLAYER,
            Platform.SELECT,
            Platform.SCENE,
            Platform.SENSOR,
            Platform.SWITCH,
            Platform.WATER_HEATER,
        ],
    )
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded
