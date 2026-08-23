# Niko Home Control II for Home Assistant

[![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)](https://github.com/makke23/niko-home-control-home-assistant/releases)
[![Validate](https://github.com/makke23/niko-home-control-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/makke23/niko-home-control-home-assistant/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An unofficial, local-first Home Assistant integration for the Niko Home
Control II Hobby API. It discovers Niko devices dynamically, exposes native
Home Assistant entities, and imports the measurement history retained by the
controller.

Maintainer: **Maarten Moortgat** ([@makke23](https://github.com/makke23))

This community project is not affiliated with or endorsed by Niko. Niko and
Niko Home Control are trademarks of their respective owner.

## Highlights

- Local TLS-MQTT control and push updates without a cloud dependency.
- Capability-driven lights, switches, covers, buttons, scenes, climate,
  ventilation, hot water, access, audio and EV-charging entities.
- Energy, water, gas, solar, battery and smart-plug measurements when the Niko
  installation exposes the corresponding capabilities.
- Automatic import of retained Niko measurement history into Home Assistant
  long-term statistics.
- Dutch and English setup flows and entity translations.
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
5. Enter the local controller address, MQTT TLS port, username and Hobby API
   token.

Do not run this integration alongside another integration using the `nhc2`
domain for the same controller; that creates duplicate devices and entities.

## Niko Energy dashboard

The integration's energy and volume sensors work with Home Assistant's native
Energy dashboard and long-term statistics without extra cards.

This repository also contains an optional, dynamically generated **Niko
Energy** YAML dashboard. HACS installs only the integration directory, so the
dashboard companion is deliberately a separate manual installation:

1. Download or clone this repository on a Windows computer that can access the
   Home Assistant configuration directory through Samba.
2. Run `install_energy_dashboard.ps1` from PowerShell.
3. The installer creates a backup of `configuration.yaml`, discovers entity
   IDs from the Home Assistant registries and writes
   `niko_energy_dashboard.yaml` into the configuration directory.
4. Validate the Home Assistant configuration and restart once when the
   dashboard is first registered. Later dashboard refreshes do not require a
   restart.

The dashboard shows only sections for equipment actually discovered in Home
Assistant. Never publish the generated dashboard, registry files, diagnostics,
logs, tokens or `configuration.yaml` without reviewing and redacting them.

## Privacy and security

- Credentials are entered in Home Assistant and are never part of this
  repository.
- `debug_config.json`, `.storage`, `secrets.yaml`, local environments, logs and
  database files are explicitly excluded from Git.
- Use `debug_config.example.json` only as a template; never commit the filled
  file.
- Read [SECURITY.md](SECURITY.md) before reporting a vulnerability or sharing
  diagnostics.

## Support and contributions

Report non-sensitive bugs through [GitHub Issues](https://github.com/makke23/niko-home-control-home-assistant/issues).
Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). The project
is released under the [MIT License](LICENSE).

## Nederlandse projectinformatie en versiehistoriek

Dit is een native Home Assistant-integratie voor de lokale Niko Home Control II Hobby API.

**Developer: Maarten Moortgat**

## Nieuw in 1.5.0

- Een optionele laadpaalpagina met laadmodus, laadstatus, live vermogen,
  geladen energie, boost en beschikbare afstandsinformatie.
- Een optionele klimaatpagina met thermostaatbediening en grafieken voor
  actuele temperatuur, doeltemperatuur, buitentemperatuur en vochtigheid.
- Laadstatus en voertuigstatus worden als Home Assistant-enumsensoren getoond.
- Witgoed met energiemeting blijft automatisch bij de slimme stopcontacten.

## Nieuw in 1.4.0

- Historische totalen voor gasmeters en Niko-batterijmeetklemmen.
- Optionele dashboardpagina's voor gas, zonneproductie en batterij laden en
  ontladen. Een pagina verschijnt alleen wanneer de bijbehorende Niko-sensoren
  werkelijk in Home Assistant aanwezig zijn.
- Meetgegevens van `centralmeter`-apparaten worden automatisch meegenomen.

## Nieuw in 1.3.0

- Detecteert automatisch de oudste beschikbare Niko-historie.
- Gebruikt dagelijkse aggregaten in blokken van maximaal 90 dagen voor oudere
  periodes en uuraggregaten voor de recentste 60 dagen. Daardoor verschijnen
  ook vorige jaren en ontbrekende maanden zonder handmatige begindatum.

## Nieuw in 1.2.1

- Voorkomt een voorlopige meterstand tijdens de eerste historische import en
  herbouwt oudere imports één keer, zodat periodegrafieken geen kunstmatige
  negatieve of positieve pieken rond het importmoment tonen.

## Nieuw in 1.2.0

- Een afzonderlijk **Niko Energie**-dashboard met live netvermogen, maandpiek,
  periodekeuze, energie- en watergrafieken en verbruik per slim stopcontact.
- Het dashboard gebruikt uitsluitend ingebouwde Home Assistant-kaarten en de
  geïmporteerde langetermijnstatistieken; een extra HACS-kaart is niet nodig.

## Nieuw in 1.1.1

- Historische aanvragen worden serieel uitgevoerd en bij tijdelijke time-outs
  automatisch opnieuw geprobeerd, zodat de Niko-controller niet wordt overbelast.

## Nieuw in 1.1.0

- Eenmalige import van alle door de Niko-controller bewaarde energie- en waterhistoriek van vóór de installatie.
- Uurwaarden worden met hun oorspronkelijke timestamp in Home Assistant-langetermijnstatistieken geschreven.
- De oudste beschikbare periode wordt automatisch ontdekt; gegevens worden vervolgens per kalenderjaar opgehaald.
- Idempotente import: na voltooiing wordt de importstatus in de entity opgeslagen en worden geen dubbele waarden aangemaakt.
- Nieuwe diagnostische entity `Historische meetgegevens importeren` met voortgang, periode en aantallen.
- Na de eerste import blijft de bestaande automatische aanvulling van gemiste intervallen actief.

## Nieuw in 1.0.2

- Eigen herkenbare Niko Home Control II-branding met subtiele developervermelding.
- Developervermelding toegevoegd aan projectmetadata en broncode.

## Nieuw in 1.0.1

- Correcte productnaam: Niko Home Control II.
- Officiële Niko Home Control II-branding voor het integratie-icoon en logo.

## Nieuw in 1.0.0

- Historische backfill voor gemiste energie- en waterintervallen na downtime.
- Scènes, alles-uit, huisstatus, aanwezigheidssimulatie, piek-/zonnemodus en alarmroutines.
- Toegangscontrole, deurontgrendeling en video-deurbelstatus.
- Partnerapparaten voor ventilatie, warm water, EV-laden en Bose/Sonos-audio.
- Tokenverval als diagnostische tijdstempel.
- Hobby API-token veilig vervangen via `Herconfigureren`, met verbindingstest en automatische reload.
- Privacy-veilige Home Assistant-diagnostiekdownload.
- HACS-distributiemetadata en uitgebreidere Nederlandse en Engelse vertalingen.

## Nieuw in 0.9.0

- Lokale Niko-alarmen en informatieve meldingen via het Home Assistant event-platform.
- Nieuwe `alarm`- en `notification`-events met tekst, Niko-tijdstip en melding-ID.
- Bestaande meldingen worden bij opstart ingelezen zonder oude events opnieuw af te vuren.
- Nieuwe meldingen zijn rechtstreeks bruikbaar als Home Assistant-automatiseringstrigger.

## Nieuw in 0.8.0

- Climate-entities voor Niko HVAC-, klassieke, Digital Black- en virtuele thermostaten.
- Actuele temperatuur, doeltemperatuur en verwarmings-/koelvraag.
- Niko-programma's als Home Assistant-presets.
- Tijdelijke temperatuur-overrule en, waar aanwezig, HVAC-modus en ventilatorsnelheid.
- Temperatuur-, gevoelstemperatuur- en luchtvochtigheidssensoren voor thermoswitches.

## Nieuw in 0.7.0

- Niko-ventilatorsnelheid als keuzelijst met `Low`, `Medium`, `High` en `Boost`.
- Ondersteuning voor Velux- en Reynaers-motoracties.
- Correcte Home Assistant-apparaatklassen voor poorten, rolluiken, zonwering, jaloezieën en ramen.
- Diagnostische status voor uitgelijnde motoren en `AllStarted`-acties.

## Nieuw in 0.6.0

- Vrije start/stop-routines als toestandsschakelaar.
- PIR-detectie correct in- en uitschakelen zonder ze als bewegingsmelding voor te stellen.
- Voorwaardelijke Niko-acties als drukknop met aparte IF/ELSE-status.
- Alleen-lezen actieve status voor tijdschema's.
- Diagnostische `AllConnected`-status voor acties die deze capability aanbieden.
- Nieuw Home Assistant `button`-platform.

## Eerder toegevoegd in 0.5.0

- Lokale Niko Measurements REST-interface voor gelogde energie- en waterintervallen.
- Persistente kWh-totalen voor netafname, netinjectie, verbruik en zelfverbruik.
- Persistente m³-waterteller.
- Energieverbruik per slimme stekker.
- Deduplicatie op de Niko-meettimestamp, zodat herstarten geen interval dubbel telt.
- Parallelle, niet-blokkerende vernieuwing om de vijf minuten.
- Geanonimiseerde live diagnose via `debug_niko_connection.py --measurements --once`.

De totalen beginnen bij nul wanneer de integratie voor het eerst wordt geïnstalleerd en groeien daarna met ieder nieuw Niko-interval. Ze worden bij een Home Assistant-herstart hersteld.

## Eerder toegevoegd in 0.4.1

- TLS-initialisatie laadt geen systeemcertificaten meer op de Home Assistant-eventloop.

## Eerder toegevoegd in 0.4.0

- Fasevermogen voor een- en driefasige Niko-meetmodules.
- Actuele en cumulatieve elektrische energie in Wh.
- Netafname, netinjectie, productie en zelfverbruik als energiesensoren.
- Water- en gasvolume in m³ voor pulsmeters en `energyhome`.
- Correcte Home Assistant device classes en state classes voor Energie-dashboards en langetermijnstatistieken.
- Meterentities kunnen al worden aangemaakt wanneer Niko de capability meldt maar de eerste meetwaarde nog niet ontvangen is.

## Eerder toegevoegd in 0.3.0

- Live vermogenssensoren voor slimme stekkers (`ElectricalPower`).
- Energiesensoren voor netafname, netinjectie en maandpiek.
- `ReportInstantUsage` wordt automatisch iedere 25 seconden opnieuw geactiveerd, omdat de Niko-controller deze snelle updates na ongeveer 30 seconden uitschakelt.
- Meerdere meettoestellen worden efficiënt in één `devices.control`-commando bijgewerkt.

## Eerder toegevoegd in 0.2.0

- Automatische capability-gedreven discovery van lampen, dimmers, schakelaars en covers.
- Bediening via het officiële `devices.control`-protocol.
- Interne hardware-records zoals `smartrelay` en `smartmotor` worden niet als dubbele entities getoond.
- Niet-blokkerende MQTT-connectie met betrouwbare time-out.
- Lopende requests stoppen onmiddellijk bij verbindingsverlies.
- Veilige verwerking van onverwachte JSON-payloads.
- Geanonimiseerd capability-overzicht via de Visual Studio-debugger.

## Wat de integratie al doet

- Configuratie via **Instellingen → Apparaten en diensten → Integratie toevoegen**.
- Rechtstreekse TLS-MQTT-verbinding met de lokale Niko Hobby API.
- `devices.list` ophalen en parsen.
- Correct unloaden en sluiten van de Paho-netwerkthread.
- Eén controller-device met twee diagnostische entities:
  - verbinding;
  - aantal gevonden apparaten.
- Lampen en dimmers ontdekken en bedienen.
- Relais en stopcontactacties als schakelaars ontdekken en bedienen.
- Rolluiken, zonwering en poorten als covers ontdekken en bedienen, inclusief positie.
- Actuele vermogensmetingen van slimme stekkers en de energiemodule.

De PIR-eigenschap `BasicState` wordt niet ten onrechte als beweging gebruikt: volgens het Niko-protocol geeft deze alleen aan of detectie is ingeschakeld. Werkelijke geprogrammeerde bewegingsmeldingen komen via de Niko-evententity binnen.

## Visual Studio: protocol debuggen

1. Voer `setup_environment.cmd` uit.
2. Vul `debug_config.json` in.
3. Start `debug_niko_connection.py`.

Voor een eenmalig geanonimiseerd overzicht van alle modellen en capabilities:

```powershell
env\Scripts\python.exe debug_niko_connection.py --capabilities --once
```

Hiermee debug je de Niko-client met breakpoints zonder Home Assistant te starten.

## Naar Home Assistant kopiëren

Via Samba:

```powershell
.\deploy_to_homeassistant.ps1
```

Of kopieer handmatig:

```text
custom_components\niko_home_control_local
```

naar:

```text
/config/custom_components/niko_home_control_local
```

Herstart Home Assistant volledig. Voeg daarna **Niko Home Control II** toe onder Apparaten en diensten.

## Eerste acceptatietest

- Integratie verschijnt in de zoeklijst.
- Config flow accepteert host, poort, gebruiker en token.
- `Aantal apparaten` komt overeen met `devices.list`.
- `Verbinding` staat aan.
- Lampen en schakelaars reageren op aan/uit.
- Rolluiken reageren op openen, sluiten, stoppen en positie.
- Vermogenssensoren worden ongeveer iedere twee seconden bijgewerkt wanneer Niko meetgegevens publiceert.
- Reload van de config entry werkt.
- Home Assistant herstart en maakt opnieuw verbinding.
- Verwijderen/unloaden laat geen MQTT-thread achter.
