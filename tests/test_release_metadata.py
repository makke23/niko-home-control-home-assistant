"""Validate public release metadata and bundled dashboard files."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "niko_home_control_local"


def test_public_version_is_consistent() -> None:
    """Keep the manifest, Python version, and release notes synchronized."""

    manifest = json.loads((INTEGRATION / "manifest.json").read_text("utf-8"))
    constants = (INTEGRATION / "const.py").read_text("utf-8")
    readme = (ROOT / "README.md").read_text("utf-8")
    match = re.search(r'^VERSION = "([^"]+)"$', constants, re.MULTILINE)

    assert match is not None
    assert manifest["version"] == match.group(1)
    assert f"### {manifest['version']}" in readme


def test_dashboard_strategy_is_bundled() -> None:
    """Ensure HACS receives the dashboard and its discovery registration."""

    dashboard = (
        INTEGRATION / "frontend" / "niko-energy-dashboard.js"
    ).read_text("utf-8")

    assert 'const STRATEGY_TYPE = "niko-energy"' in dashboard
    assert "ll-strategy-dashboard-${STRATEGY_TYPE}" in dashboard
    assert "window.customStrategies.push" in dashboard
    assert 'type: "config/entity_registry/list"' in dashboard
    assert 'type: "config/device_registry/list"' in dashboard


def test_legacy_dashboard_installer_is_removed() -> None:
    """Prevent reintroducing machine-specific YAML dashboard deployment."""

    assert not (ROOT / "install_energy_dashboard.ps1").exists()
    assert not (ROOT / "niko_energy_dashboard.yaml").exists()


def test_device_topology_uses_current_registry_api() -> None:
    """Avoid the deprecated via_device field that blocks entity setup."""

    entity_source = (INTEGRATION / "entity.py").read_text("utf-8")
    setup_source = (INTEGRATION / "__init__.py").read_text("utf-8")

    assert "via_device=" not in entity_source
    assert 'info["via_device_id"]' in entity_source
    assert "hub.device_registry_id = controller.id" in setup_source
