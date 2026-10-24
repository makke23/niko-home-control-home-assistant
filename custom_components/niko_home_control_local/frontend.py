"""Register the Niko Energy community dashboard strategy."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION

_DASHBOARD_FILENAME = "niko-energy-dashboard.js"
_DASHBOARD_URL = f"/{DOMAIN}/frontend/{_DASHBOARD_FILENAME}"
_REGISTERED = "dashboard_strategy_registered"


async def async_register_dashboard_strategy(hass: HomeAssistant) -> None:
    """Serve and load the dashboard strategy bundled with the integration."""

    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    integration_data = hass.data.setdefault(DOMAIN, {})
    if integration_data.get(_REGISTERED):
        return

    dashboard_path = Path(__file__).parent / "frontend" / _DASHBOARD_FILENAME
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                _DASHBOARD_URL,
                str(dashboard_path),
                cache_headers=True,
            )
        ]
    )
    add_extra_js_url(hass, f"{_DASHBOARD_URL}?v={VERSION}")
    integration_data[_REGISTERED] = True
