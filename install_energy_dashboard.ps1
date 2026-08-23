param(
    [string]$HomeAssistantConfig = "\\homeassistant\config"
)

$ErrorActionPreference = "Stop"

$dashboardSource = Join-Path $PSScriptRoot "niko_energy_dashboard.yaml"
$dashboardDestination = Join-Path `
    $HomeAssistantConfig `
    "niko_energy_dashboard.yaml"
$configurationPath = Join-Path $HomeAssistantConfig "configuration.yaml"

if (-not (Test-Path -LiteralPath $HomeAssistantConfig)) {
    throw "De Home Assistant-configuratiemap is niet bereikbaar: $HomeAssistantConfig"
}

if (-not (Test-Path -LiteralPath $dashboardSource)) {
    throw "Het Niko-energiedashboard ontbreekt: $dashboardSource"
}

if (-not (Test-Path -LiteralPath $configurationPath)) {
    throw "configuration.yaml ontbreekt in $HomeAssistantConfig"
}

$dashboard = Get-Content -LiteralPath $dashboardSource -Raw

$entityRegistryPath = Join-Path `
    $HomeAssistantConfig `
    ".storage\core.entity_registry"
$integrationEntities = @()
$devicesById = @{}
if (Test-Path -LiteralPath $entityRegistryPath) {
    try {
        $entityRegistry = Get-Content `
            -LiteralPath $entityRegistryPath `
            -Raw |
            ConvertFrom-Json
        $integrationEntities = @(
            $entityRegistry.data.entities |
                Where-Object { $_.platform -eq "niko_home_control_local" }
        )
    }
    catch {
        Write-Warning "De Home Assistant-entiteitslijst kon niet worden gelezen. Standaardnamen worden gebruikt."
    }
}

$deviceRegistryPath = Join-Path `
    $HomeAssistantConfig `
    ".storage\core.device_registry"
if (Test-Path -LiteralPath $deviceRegistryPath) {
    try {
        $deviceRegistry = Get-Content `
            -LiteralPath $deviceRegistryPath `
            -Raw |
            ConvertFrom-Json
        $deviceRegistry.data.devices | ForEach-Object {
            $devicesById[[string]$_.id] = $_
        }
    }
    catch {
        Write-Warning "De Home Assistant-apparatenlijst kon niet worden gelezen."
    }
}

function Find-NikoEntityId {
    param(
        [string]$UniqueIdSuffix,
        [string]$Fallback
    )

    $match = $integrationEntities |
        Where-Object { $_.unique_id -like "*$UniqueIdSuffix" } |
        Select-Object -First 1
    if ($null -ne $match) {
        return [string]$match.entity_id
    }
    return $Fallback
}

$dashboardEntities = [ordered]@{
    "__NIKO_NET_FROM_GRID_POWER__" = Find-NikoEntityId `
        -UniqueIdSuffix "_ElectricalPowerFromGrid" `
        -Fallback "sensor.energyhome_energyhome_electricalpowerfromgrid"
    "__NIKO_NET_TO_GRID_POWER__" = Find-NikoEntityId `
        -UniqueIdSuffix "_ElectricalPowerToGrid" `
        -Fallback "sensor.energyhome_energyhome_electricalpowertogrid"
    "__NIKO_MONTHLY_PEAK__" = Find-NikoEntityId `
        -UniqueIdSuffix "_ElectricalMonthlyPeakPowerFromGrid" `
        -Fallback "sensor.energyhome_energyhome_monthly_peak_power"
    "__NIKO_GRID_IMPORT_TOTAL__" = Find-NikoEntityId `
        -UniqueIdSuffix "_ElectricalEnergyFromGrid_total" `
        -Fallback "sensor.energyhome_netafname_totaal"
    "__NIKO_GRID_EXPORT_TOTAL__" = Find-NikoEntityId `
        -UniqueIdSuffix "_ElectricalEnergyToGrid_total" `
        -Fallback "sensor.energyhome_netinjectie_totaal"
}

foreach ($placeholder in $dashboardEntities.Keys) {
    $dashboard = $dashboard.Replace(
        $placeholder,
        $dashboardEntities[$placeholder]
    )
}

$chargerDeviceKeys = @{}
$integrationEntities |
    Where-Object {
        $_.unique_id -like "*_charging_mode" -or
            $_.unique_id -like "*_Chargingstatus" -or
            $_.unique_id -like "*_EVStatus"
    } |
    ForEach-Object {
        $key = $_.unique_id -replace `
            "_(?:charging_mode|Chargingstatus|EVStatus)$", `
            ""
        $chargerDeviceKeys[$key] = $true
    }

$smartPlugPowerEntities = @(
    $integrationEntities |
        Where-Object {
            if ($_.unique_id -notlike "*_ElectricalPower") {
                return $false
            }
            $deviceKey = $_.unique_id -replace "_ElectricalPower$", ""
            if ($chargerDeviceKeys.ContainsKey($deviceKey)) {
                return $false
            }
            if (-not $devicesById.ContainsKey([string]$_.device_id)) {
                return $true
            }
            $model = [string]$devicesById[[string]$_.device_id].model
            return $model -in @("generic", "naso")
        } |
        Sort-Object entity_id
)
$smartPlugEnergyByDevice = @{}
$integrationEntities |
    Where-Object { $_.unique_id -like "*_ElectricalEnergy_total" } |
    ForEach-Object {
        $deviceKey = $_.unique_id -replace "_ElectricalEnergy_total$", ""
        $smartPlugEnergyByDevice[$deviceKey] = $_
    }

if ($smartPlugPowerEntities.Count -eq 0) {
    $smartPlugLiveBlock = @"
          - type: markdown
            content: >-
              Er zijn nog geen slimme-stopcontactmetingen gevonden. Herstart
              Home Assistant en voer het deployscript daarna nogmaals uit.
"@
    $smartPlugGraphBlock = @"
          - type: markdown
            content: Geen stopcontactgeschiedenis beschikbaar.
"@
}
else {
    $liveLines = [System.Collections.Generic.List[string]]::new()
    $liveLines.Add("          - type: entities")
    $liveLines.Add("            title: Actueel vermogen")
    $liveLines.Add("            show_header_toggle: false")
    $liveLines.Add("            entities:")

    $historyLines = [System.Collections.Generic.List[string]]::new()
    $historyLines.Add("          - type: history-graph")
    $historyLines.Add("            title: Vermogen - laatste 24 uur")
    $historyLines.Add("            hours_to_show: 24")
    $historyLines.Add("            entities:")

    $graphLines = [System.Collections.Generic.List[string]]::new()
    foreach ($powerEntity in $smartPlugPowerEntities) {
        $deviceKey = $powerEntity.unique_id -replace "_ElectricalPower$", ""
        $displayName = [string]$powerEntity.original_name
        if ([string]::IsNullOrWhiteSpace($displayName)) {
            $displayName = [string]$powerEntity.entity_id
        }
        $displayName = $displayName -replace "\s+Vermogen$", ""
        $yamlName = $displayName.Replace("'", "''")

        $liveLines.Add("              - entity: $($powerEntity.entity_id)")
        $liveLines.Add("                name: '$yamlName'")
        $historyLines.Add("              - entity: $($powerEntity.entity_id)")
        $historyLines.Add("                name: '$yamlName'")

        $energyEntity = $smartPlugEnergyByDevice[$deviceKey]
        if ($null -eq $energyEntity) {
            continue
        }
        $graphLines.Add("          - type: statistics-graph")
        $graphLines.Add("            title: '$yamlName'")
        $graphLines.Add("            chart_type: bar")
        $graphLines.Add("            entities:")
        $graphLines.Add("              - entity: $($energyEntity.entity_id)")
        $graphLines.Add("                name: Verbruik")
        $graphLines.Add("            stat_types:")
        $graphLines.Add("              - change")
        $graphLines.Add("            energy_date_selection: true")
        $graphLines.Add("            collection_key: energy_niko_smart_plugs")
        $graphLines.Add("            min_y_axis: 0")
        $graphLines.Add("            fit_y_data: true")
    }

    $smartPlugLiveBlock = ($liveLines + @('') + $historyLines) -join "`r`n"
    if ($graphLines.Count -eq 0) {
        $smartPlugGraphBlock = @"
          - type: markdown
            content: Er zijn nog geen energietotalen voor de stopcontacten beschikbaar.
"@
    }
    else {
        $smartPlugGraphBlock = $graphLines -join "`r`n"
    }
}

$dashboard = $dashboard.Replace(
    "          # __NIKO_SMART_PLUG_LIVE__",
    $smartPlugLiveBlock.TrimEnd()
)
$dashboard = $dashboard.Replace(
    "          # __NIKO_SMART_PLUG_GRAPHS__",
    $smartPlugGraphBlock.TrimEnd()
)

function Get-NikoDisplayName {
    param(
        [object]$Entity,
        [string]$SuffixPattern
    )

    $name = [string]$Entity.original_name
    if ([string]::IsNullOrWhiteSpace($name)) {
        $name = [string]$Entity.entity_id
    }
    return ($name -replace $SuffixPattern, "").Replace("'", "''")
}

$optionalViewLines = [System.Collections.Generic.List[string]]::new()
$waterEntities = @(
    $integrationEntities |
        Where-Object { $_.unique_id -like "*_WaterVolume_total" } |
        Sort-Object entity_id
)
if ($waterEntities.Count -gt 0) {
    $optionalViewLines.Add("  - title: Water")
    $optionalViewLines.Add("    path: water")
    $optionalViewLines.Add("    icon: mdi:water")
    $optionalViewLines.Add("    panel: true")
    $optionalViewLines.Add("    cards:")
    $optionalViewLines.Add("      - type: vertical-stack")
    $optionalViewLines.Add("        cards:")
    $optionalViewLines.Add("          - type: energy-date-selection")
    $optionalViewLines.Add("            collection_key: energy_niko_water")
    $optionalViewLines.Add("          - type: statistic")
    $optionalViewLines.Add("            entity: $($waterEntities[0].entity_id)")
    $optionalViewLines.Add("            name: Waterverbruik in periode")
    $optionalViewLines.Add("            icon: mdi:water")
    $optionalViewLines.Add("            unit: m³")
    $optionalViewLines.Add("            stat_type: change")
    $optionalViewLines.Add("            period: energy_date_selection")
    $optionalViewLines.Add("            collection_key: energy_niko_water")
    $optionalViewLines.Add("          - type: statistics-graph")
    $optionalViewLines.Add("            title: Waterverbruik")
    $optionalViewLines.Add("            chart_type: bar")
    $optionalViewLines.Add("            entities:")
    foreach ($waterEntity in $waterEntities) {
        $name = Get-NikoDisplayName $waterEntity "\s+Waterverbruik totaal$"
        $optionalViewLines.Add("              - entity: $($waterEntity.entity_id)")
        $optionalViewLines.Add("                name: '$name'")
    }
    $optionalViewLines.Add("            stat_types:")
    $optionalViewLines.Add("              - change")
    $optionalViewLines.Add("            energy_date_selection: true")
    $optionalViewLines.Add("            collection_key: energy_niko_water")
    $optionalViewLines.Add("            min_y_axis: 0")
    $optionalViewLines.Add("            fit_y_data: true")
}

$gasEntities = @(
    $integrationEntities |
        Where-Object {
            $_.unique_id -match "_(?:GasVolume|Gasvolume)_total$"
        } |
        Sort-Object entity_id
)
if ($gasEntities.Count -gt 0) {
    $optionalViewLines.Add("  - title: Gas")
    $optionalViewLines.Add("    path: gas")
    $optionalViewLines.Add("    icon: mdi:meter-gas")
    $optionalViewLines.Add("    panel: true")
    $optionalViewLines.Add("    cards:")
    $optionalViewLines.Add("      - type: vertical-stack")
    $optionalViewLines.Add("        cards:")
    $optionalViewLines.Add("          - type: energy-date-selection")
    $optionalViewLines.Add("            collection_key: energy_niko_gas")
    $optionalViewLines.Add("          - type: statistic")
    $optionalViewLines.Add("            entity: $($gasEntities[0].entity_id)")
    $optionalViewLines.Add("            name: Gasverbruik in periode")
    $optionalViewLines.Add("            icon: mdi:meter-gas")
    $optionalViewLines.Add("            unit: m³")
    $optionalViewLines.Add("            stat_type: change")
    $optionalViewLines.Add("            period: energy_date_selection")
    $optionalViewLines.Add("            collection_key: energy_niko_gas")
    $optionalViewLines.Add("          - type: statistics-graph")
    $optionalViewLines.Add("            title: Gasverbruik")
    $optionalViewLines.Add("            chart_type: bar")
    $optionalViewLines.Add("            entities:")
    foreach ($gasEntity in $gasEntities) {
        $name = Get-NikoDisplayName $gasEntity "\s+Gasverbruik totaal$"
        $optionalViewLines.Add("              - entity: $($gasEntity.entity_id)")
        $optionalViewLines.Add("                name: '$name'")
    }
    $optionalViewLines.Add("            stat_types:")
    $optionalViewLines.Add("              - change")
    $optionalViewLines.Add("            energy_date_selection: true")
    $optionalViewLines.Add("            collection_key: energy_niko_gas")
    $optionalViewLines.Add("            min_y_axis: 0")
    $optionalViewLines.Add("            fit_y_data: true")
}

$solarEntities = @(
    $integrationEntities |
        Where-Object {
            $_.unique_id -like "*_ElectricalEnergyProduction_total"
        } |
        Sort-Object entity_id
)
if ($solarEntities.Count -gt 0) {
    $optionalViewLines.Add("  - title: Zonne-energie")
    $optionalViewLines.Add("    path: zonne-energie")
    $optionalViewLines.Add("    icon: mdi:solar-power")
    $optionalViewLines.Add("    panel: true")
    $optionalViewLines.Add("    cards:")
    $optionalViewLines.Add("      - type: vertical-stack")
    $optionalViewLines.Add("        cards:")
    $optionalViewLines.Add("          - type: energy-date-selection")
    $optionalViewLines.Add("            collection_key: energy_niko_solar")
    $optionalViewLines.Add("          - type: statistic")
    $optionalViewLines.Add("            entity: $($solarEntities[0].entity_id)")
    $optionalViewLines.Add("            name: Productie in periode")
    $optionalViewLines.Add("            icon: mdi:solar-power")
    $optionalViewLines.Add("            unit: kWh")
    $optionalViewLines.Add("            stat_type: change")
    $optionalViewLines.Add("            period: energy_date_selection")
    $optionalViewLines.Add("            collection_key: energy_niko_solar")
    $optionalViewLines.Add("          - type: statistics-graph")
    $optionalViewLines.Add("            title: Zonneproductie")
    $optionalViewLines.Add("            chart_type: bar")
    $optionalViewLines.Add("            entities:")
    foreach ($solarEntity in $solarEntities) {
        $name = Get-NikoDisplayName $solarEntity "\s+Productie totaal$"
        $optionalViewLines.Add("              - entity: $($solarEntity.entity_id)")
        $optionalViewLines.Add("                name: '$name'")
    }
    $optionalViewLines.Add("            stat_types:")
    $optionalViewLines.Add("              - change")
    $optionalViewLines.Add("            energy_date_selection: true")
    $optionalViewLines.Add("            collection_key: energy_niko_solar")
    $optionalViewLines.Add("            min_y_axis: 0")
    $optionalViewLines.Add("            fit_y_data: true")
}

$batteryEnergyEntities = @(
    $integrationEntities |
        Where-Object {
            $_.unique_id -match "_ElectricalEnergy(?:Charged|Discharged)_total$"
        } |
        Sort-Object entity_id
)
if ($batteryEnergyEntities.Count -gt 0) {
    $batteryDeviceKeys = @{}
    foreach ($batteryEntity in $batteryEnergyEntities) {
        $key = $batteryEntity.unique_id -replace `
            "_ElectricalEnergy(?:Charged|Discharged)_total$", `
            ""
        $batteryDeviceKeys[$key] = $true
    }
    $batteryPowerEntities = @(
        $integrationEntities |
            Where-Object {
                $key = $_.unique_id -replace "_ElectricalPower$", ""
                $_.unique_id -like "*_ElectricalPower" -and
                    $batteryDeviceKeys.ContainsKey($key)
            } |
            Sort-Object entity_id
    )

    $optionalViewLines.Add("  - title: Batterij")
    $optionalViewLines.Add("    path: batterij")
    $optionalViewLines.Add("    icon: mdi:home-battery")
    $optionalViewLines.Add("    panel: true")
    $optionalViewLines.Add("    cards:")
    $optionalViewLines.Add("      - type: vertical-stack")
    $optionalViewLines.Add("        cards:")
    if ($batteryPowerEntities.Count -gt 0) {
        $optionalViewLines.Add("          - type: entities")
        $optionalViewLines.Add("            title: Actueel batterijvermogen")
        $optionalViewLines.Add("            show_header_toggle: false")
        $optionalViewLines.Add("            entities:")
        foreach ($powerEntity in $batteryPowerEntities) {
            $name = Get-NikoDisplayName $powerEntity "\s+Vermogen$"
            $optionalViewLines.Add("              - entity: $($powerEntity.entity_id)")
            $optionalViewLines.Add("                name: '$name'")
        }
    }
    $optionalViewLines.Add("          - type: energy-date-selection")
    $optionalViewLines.Add("            collection_key: energy_niko_battery")
    $optionalViewLines.Add("          - type: statistics-graph")
    $optionalViewLines.Add("            title: Laden en ontladen")
    $optionalViewLines.Add("            chart_type: bar")
    $optionalViewLines.Add("            entities:")
    foreach ($batteryEntity in $batteryEnergyEntities) {
        $deviceName = Get-NikoDisplayName `
            $batteryEntity `
            "\s+Batterij (?:geladen|ontladen) totaal$"
        $direction = if (
            $batteryEntity.unique_id -like "*_ElectricalEnergyCharged_total"
        ) {
            "Laden"
        }
        else {
            "Ontladen"
        }
        $optionalViewLines.Add("              - entity: $($batteryEntity.entity_id)")
        $optionalViewLines.Add("                name: '$deviceName - $direction'")
    }
    $optionalViewLines.Add("            stat_types:")
    $optionalViewLines.Add("              - change")
    $optionalViewLines.Add("            energy_date_selection: true")
    $optionalViewLines.Add("            collection_key: energy_niko_battery")
    $optionalViewLines.Add("            min_y_axis: 0")
    $optionalViewLines.Add("            fit_y_data: true")
}

if ($chargerDeviceKeys.Count -gt 0) {
    $chargerEntities = @(
        $integrationEntities |
            Where-Object {
                $uniqueId = [string]$_.unique_id
                foreach ($key in $chargerDeviceKeys.Keys) {
                    if ($uniqueId -eq $key -or $uniqueId -like "${key}_*") {
                        return $true
                    }
                }
                return $false
            } |
            Sort-Object entity_id
    )
    $chargerPowerEntities = @(
        $chargerEntities |
            Where-Object { $_.unique_id -like "*_ElectricalPower" }
    )
    $chargerEnergyEntities = @(
        $chargerEntities |
            Where-Object { $_.unique_id -like "*_ElectricalEnergy_total" }
    )
    $chargerStatusEntities = @(
        $chargerEntities |
            Where-Object {
                $_.unique_id -notlike "*_ElectricalPower" -and
                    $_.unique_id -notlike "*_ElectricalEnergy*"
            }
    )

    $optionalViewLines.Add("  - title: Laadpaal")
    $optionalViewLines.Add("    path: laadpaal")
    $optionalViewLines.Add("    icon: mdi:ev-station")
    $optionalViewLines.Add("    panel: true")
    $optionalViewLines.Add("    cards:")
    $optionalViewLines.Add("      - type: vertical-stack")
    $optionalViewLines.Add("        cards:")
    if ($chargerStatusEntities.Count -gt 0) {
        $optionalViewLines.Add("          - type: entities")
        $optionalViewLines.Add("            title: Laadpaalstatus en bediening")
        $optionalViewLines.Add("            show_header_toggle: false")
        $optionalViewLines.Add("            entities:")
        foreach ($entity in $chargerStatusEntities) {
            $name = Get-NikoDisplayName $entity "^$"
            $optionalViewLines.Add("              - entity: $($entity.entity_id)")
            $optionalViewLines.Add("                name: '$name'")
        }
    }
    if ($chargerPowerEntities.Count -gt 0) {
        $optionalViewLines.Add("          - type: history-graph")
        $optionalViewLines.Add("            title: Laadvermogen - laatste 24 uur")
        $optionalViewLines.Add("            hours_to_show: 24")
        $optionalViewLines.Add("            entities:")
        foreach ($entity in $chargerPowerEntities) {
            $name = Get-NikoDisplayName $entity "\s+Vermogen$"
            $optionalViewLines.Add("              - entity: $($entity.entity_id)")
            $optionalViewLines.Add("                name: '$name'")
        }
    }
    if ($chargerEnergyEntities.Count -gt 0) {
        $optionalViewLines.Add("          - type: energy-date-selection")
        $optionalViewLines.Add("            collection_key: energy_niko_chargers")
        $optionalViewLines.Add("          - type: statistics-graph")
        $optionalViewLines.Add("            title: Geladen energie")
        $optionalViewLines.Add("            chart_type: bar")
        $optionalViewLines.Add("            entities:")
        foreach ($entity in $chargerEnergyEntities) {
            $name = Get-NikoDisplayName $entity "\s+Energie totaal$"
            $optionalViewLines.Add("              - entity: $($entity.entity_id)")
            $optionalViewLines.Add("                name: '$name'")
        }
        $optionalViewLines.Add("            stat_types:")
        $optionalViewLines.Add("              - change")
        $optionalViewLines.Add("            energy_date_selection: true")
        $optionalViewLines.Add("            collection_key: energy_niko_chargers")
        $optionalViewLines.Add("            min_y_axis: 0")
        $optionalViewLines.Add("            fit_y_data: true")
    }
}

$climateEntities = @(
    $integrationEntities |
        Where-Object { $_.entity_id -like "climate.*" } |
        Sort-Object entity_id
)
if ($climateEntities.Count -gt 0) {
    $optionalViewLines.Add("  - title: Klimaat")
    $optionalViewLines.Add("    path: klimaat")
    $optionalViewLines.Add("    icon: mdi:home-thermometer")
    $optionalViewLines.Add("    panel: true")
    $optionalViewLines.Add("    cards:")
    $optionalViewLines.Add("      - type: vertical-stack")
    $optionalViewLines.Add("        cards:")
    $optionalViewLines.Add("          - type: grid")
    $optionalViewLines.Add("            columns: 2")
    $optionalViewLines.Add("            square: false")
    $optionalViewLines.Add("            cards:")
    foreach ($climateEntity in $climateEntities) {
        $climateName = Get-NikoDisplayName $climateEntity "^$"
        $optionalViewLines.Add("              - type: thermostat")
        $optionalViewLines.Add("                entity: $($climateEntity.entity_id)")
        $optionalViewLines.Add("                name: '$climateName'")
    }

    foreach ($climateEntity in $climateEntities) {
        $deviceId = [string]$climateEntity.device_id
        $temperatureEntities = @(
            $integrationEntities |
                Where-Object {
                    [string]$_.device_id -eq $deviceId -and
                        $_.unique_id -match `
                            "_(?:AmbientTemperature|SetpointTemperature|OverruleSetpoint|OutdoorTemperature)$"
                } |
                Sort-Object entity_id
        )
        if ($temperatureEntities.Count -gt 0) {
            $climateName = Get-NikoDisplayName $climateEntity "^$"
            $optionalViewLines.Add("          - type: history-graph")
            $optionalViewLines.Add("            title: '$climateName - temperatuur'")
            $optionalViewLines.Add("            hours_to_show: 24")
            $optionalViewLines.Add("            entities:")
            foreach ($entity in $temperatureEntities) {
                $name = Get-NikoDisplayName $entity "^$"
                $optionalViewLines.Add("              - entity: $($entity.entity_id)")
                $optionalViewLines.Add("                name: '$name'")
            }
        }

        $humidityEntities = @(
            $integrationEntities |
                Where-Object {
                    [string]$_.device_id -eq $deviceId -and
                        $_.unique_id -like "*_Humidity"
                } |
                Sort-Object entity_id
        )
        if ($humidityEntities.Count -gt 0) {
            $climateName = Get-NikoDisplayName $climateEntity "^$"
            $optionalViewLines.Add("          - type: history-graph")
            $optionalViewLines.Add("            title: '$climateName - luchtvochtigheid'")
            $optionalViewLines.Add("            hours_to_show: 24")
            $optionalViewLines.Add("            entities:")
            foreach ($entity in $humidityEntities) {
                $name = Get-NikoDisplayName $entity "^$"
                $optionalViewLines.Add("              - entity: $($entity.entity_id)")
                $optionalViewLines.Add("                name: '$name'")
            }
        }
    }
}

$dashboard = $dashboard.Replace(
    "  # __NIKO_OPTIONAL_VIEWS__",
    ($optionalViewLines -join "`r`n").TrimEnd()
)

$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText(
    $dashboardDestination,
    $dashboard,
    $utf8WithoutBom
)

$lines = [System.Collections.Generic.List[string]]::new()
Get-Content -LiteralPath $configurationPath | ForEach-Object {
    $lines.Add($_)
}

if ($lines -match '^    niko-energy:\s*(?:#.*)?$') {
    Write-Host "Niko Energie-dashboard was al geregistreerd."
    Write-Host "Dashboardbestand is bijgewerkt: $dashboardDestination"
    exit 0
}

$lovelaceIndex = -1
for ($index = 0; $index -lt $lines.Count; $index++) {
    if ($lines[$index] -match '^lovelace:\s*(?:#.*)?$') {
        $lovelaceIndex = $index
        break
    }
}

$dashboardRegistration = [string[]]@(
    '    niko-energy:',
    '      mode: yaml',
    '      filename: niko_energy_dashboard.yaml',
    '      title: Niko Energie',
    '      icon: mdi:lightning-bolt',
    '      show_in_sidebar: true',
    '      require_admin: false'
)

if ($lovelaceIndex -eq -1) {
    if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne '') {
        $lines.Add('')
    }
    $lines.Add('lovelace:')
    $lines.Add('  dashboards:')
    $lines.AddRange($dashboardRegistration)
}
else {
    $lovelaceEnd = $lines.Count
    for ($index = $lovelaceIndex + 1; $index -lt $lines.Count; $index++) {
        if (
            $lines[$index] -match '^[A-Za-z0-9_][A-Za-z0-9_-]*:' -and
            $lines[$index] -notmatch '^\s'
        ) {
            $lovelaceEnd = $index
            break
        }
    }

    $dashboardsIndex = -1
    for ($index = $lovelaceIndex + 1; $index -lt $lovelaceEnd; $index++) {
        if ($lines[$index] -match '^  dashboards:\s*(?:#.*)?$') {
            $dashboardsIndex = $index
            break
        }
    }

    if ($dashboardsIndex -eq -1) {
        $newLines = [string[]](@('  dashboards:') + $dashboardRegistration)
        $lines.InsertRange($lovelaceEnd, $newLines)
    }
    else {
        $lines.InsertRange($dashboardsIndex + 1, $dashboardRegistration)
    }
}

$backupPath = "$configurationPath.niko-dashboard-backup"
Copy-Item -LiteralPath $configurationPath -Destination $backupPath -Force

[System.IO.File]::WriteAllLines($configurationPath, $lines, $utf8WithoutBom)

Write-Host ""
Write-Host "Niko Energie-dashboard geïnstalleerd."
Write-Host "Dashboardbestand: $dashboardDestination"
Write-Host "Configuratieback-up: $backupPath"
Write-Host "Na een configuratiecontrole is één herstart van Home Assistant nodig."
