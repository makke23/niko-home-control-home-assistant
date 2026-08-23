# Niko Home Control II for Home Assistant

[![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)](https://github.com/makke23/niko-home-control-home-assistant/releases)
[![Validate](https://github.com/makke23/niko-home-control-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/makke23/niko-home-control-home-assistant/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An unofficial, local-first Home Assistant integration for the Niko Home
Control II Hobby API. It discovers Niko devices dynamically, exposes native
Home Assistant entities, and imports measurement history retained by the
controller.

Maintainer: **Maarten Moortgat** ([@makke23](https://github.com/makke23))

This community project is not affiliated with or endorsed by Niko. Niko and
Niko Home Control are trademarks of their respective owner.

## Highlights

- Local TLS-MQTT control and push updates without a cloud dependency.
- Capability-driven lights, switches, covers, buttons, scenes, climate,
  ventilation, hot water, access, audio, and EV-charging entities.
- Energy, water, gas, solar, battery, and smart-plug measurements when the Niko
  installation exposes the corresponding capabilities.
- Automatic import of retained Niko measurement history into Home Assistant
  long-term statistics.
- English source text with Dutch and English setup-flow translations.
- Privacy-safe diagnostics with credentials and identifying connection data
  removed.

## Requirements

- Home Assistant with access to the Niko controller on the local network.
- Niko Home Control II with the Hobby API enabled.
- The controller address and a valid Hobby API token.

See the [official Niko Hobby API information](https://www.niko.eu/en/need-help/faq/niko-home-control-api)
for availability and token setup.

## Installation with HACS

Until this repository is accepted into the default HACS catalogue, add it as a
custom repository:

1. Open **HACS → three-dot menu → Custom repositories**.
2. Add `https://github.com/makke23/niko-home-control-home-assistant` and select
   **Integration** as the category.
3. Download **Niko Home Control II** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and search for
   **Niko Home Control II**.
5. Enter the local controller address, MQTT TLS port, username, and Hobby API
   token.

Do not run this integration alongside another integration using the `nhc2`
domain for the same controller; that creates duplicate devices and entities.

The request for inclusion in the default HACS catalogue is tracked in
[hacs/default#10257](https://github.com/hacs/default/pull/10257).

## Niko Energy dashboard

The integration's energy and volume sensors work with Home Assistant's native
Energy dashboard and long-term statistics without extra cards.

This repository also contains an optional, dynamically generated **Niko
Energy** YAML dashboard. HACS installs only the integration directory, so the
dashboard companion is deliberately a separate manual installation:

1. Download or clone this repository on a Windows computer that can access the
   Home Assistant configuration directory through Samba.
2. Run `install_energy_dashboard.ps1` from PowerShell.
3. The installer backs up `configuration.yaml`, discovers entity IDs from the
   Home Assistant registries, and writes `niko_energy_dashboard.yaml` into the
   configuration directory.
4. Validate the Home Assistant configuration and restart once when the
   dashboard is first registered. Later dashboard refreshes do not require a
   restart.

The dashboard shows only sections for equipment actually discovered in Home
Assistant. Never publish generated dashboards, registry files, diagnostics,
logs, tokens, or `configuration.yaml` without reviewing and redacting them.

## Privacy and security

- Credentials are entered in Home Assistant and are never part of this
  repository.
- `debug_config.json`, `.storage`, `secrets.yaml`, local environments, logs,
  and database files are explicitly excluded from Git.
- Use `debug_config.example.json` only as a template; never commit the filled
  file.
- Read [SECURITY.md](SECURITY.md) before reporting a vulnerability or sharing
  diagnostics.

## Release history

### 1.6.0

- Standardized public documentation, dashboard text, sensor names, helper
  scripts, and diagnostic output in English.
- Retained Dutch setup-flow translations and compatibility with existing Dutch
  entity names in the dashboard installer.

### 1.5.0

- Added optional EV-charging and climate dashboard pages.
- Added enum sensors for charging and vehicle status.
- Kept energy-monitored appliances grouped with smart plugs.

### 1.4.0

- Added historical gas and Niko battery totals.
- Added optional gas, solar-production, and battery dashboard pages.
- Included measurements from `centralmeter` devices.

### 1.3.0

- Automatically discovers the oldest retained Niko history.
- Uses daily aggregates for older periods and hourly aggregates for the most
  recent 60 days.

### 1.2.0–1.2.1

- Added the separate Niko Energy dashboard using only built-in Home Assistant
  cards.
- Prevented provisional totals during first import from producing artificial
  positive or negative chart spikes.

### 1.1.0–1.1.1

- Added a one-time import of all retained pre-installation energy and water
  history.
- Added serialized requests, retries, idempotent imports, and a diagnostic
  history-import entity.

### 1.0.0–1.0.2

- Added missed-interval backfill, scenes, routines, access control, doorbell
  status, partner devices, token expiry, credential reconfiguration, privacy-
  safe diagnostics, distribution metadata, and project branding.

### 0.8.0–0.9.0

- Added climate entities, thermostat presets, ventilation levels, and local
  alarm and notification events.

### 0.5.0–0.7.0

- Added the local measurements REST interface, persisted energy and volume
  totals, smart-plug consumption, more cover models, stateful routines,
  conditional actions, and diagnostic statuses.

### 0.2.0–0.4.1

- Added capability-driven discovery, native controls, reliable MQTT lifecycle,
  live power and phase measurements, energy/volume sensors, long-term statistics,
  and safe TLS initialization.

## Development and protocol debugging

1. Run `setup_environment.cmd`.
2. Copy `debug_config.example.json` to `debug_config.json`.
3. Add local test credentials only to `debug_config.json`; it is excluded from
   Git.
4. Start `debug_niko_connection.py`.

For a one-time anonymized capability summary:

```powershell
env\Scripts\python.exe debug_niko_connection.py --capabilities --once
```

The other anonymized probes are available through `--measurements`,
`--history`, `--history-levels`, and `--notifications`.

## Manual deployment

Deploy through Samba:

```powershell
.\deploy_to_homeassistant.ps1
```

Alternatively, copy:

```text
custom_components\niko_home_control_local
```

to:

```text
/config/custom_components/niko_home_control_local
```

Validate the Home Assistant configuration and restart Home Assistant. Then add
**Niko Home Control II** under **Settings → Devices & services**.

## Acceptance checklist

- The integration appears in the add-integration search.
- The config flow accepts the host, port, username, and token.
- The device count matches `devices.list`.
- The connection diagnostic is active.
- Lights, switches, and covers respond correctly.
- Measurement sensors update when Niko publishes new values.
- Config-entry reload and Home Assistant restart reconnect cleanly.
- Removing or unloading the integration leaves no MQTT thread running.

## Support and contributions

Report non-sensitive bugs through [GitHub Issues](https://github.com/makke23/niko-home-control-home-assistant/issues).
Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). The project
is released under the [MIT License](LICENSE).
