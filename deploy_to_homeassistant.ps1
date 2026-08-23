param(
    [string]$HomeAssistantConfig = "\\homeassistant\config"
)

$ErrorActionPreference = "Stop"

$source = Join-Path `
    $PSScriptRoot `
    "custom_components\niko_home_control_local"

$destination = Join-Path `
    $HomeAssistantConfig `
    "custom_components\niko_home_control_local"

Write-Host "Bron:"
Write-Host "  $source"

Write-Host "Bestemming:"
Write-Host "  $destination"

if (-not (Test-Path -LiteralPath $source)) {
    throw "De bronmap bestaat niet: $source"
}

if (-not (Test-Path -LiteralPath $HomeAssistantConfig)) {
    throw @"
De Home Assistant Samba-share is niet bereikbaar:

$HomeAssistantConfig

Open eerst in Windows Verkenner:
\\homeassistant\config

Meld je daar aan met de gebruikersgegevens van de Samba Share-app.
Gebruik eventueel het IP-adres van Home Assistant in plaats van 'homeassistant'.
"@
}

$customComponentsDirectory = Join-Path `
    $HomeAssistantConfig `
    "custom_components"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $customComponentsDirectory |
    Out-Null

Write-Host "Integratie kopiëren..."

$destinationManifestBefore = Join-Path $destination "manifest.json"
$previousDestinationVersion = $null
if (Test-Path -LiteralPath $destinationManifestBefore) {
    try {
        $previousDestinationVersion = (
            Get-Content -LiteralPath $destinationManifestBefore -Raw |
                ConvertFrom-Json
        ).version
    }
    catch {
        $previousDestinationVersion = $null
    }
}

robocopy `
    $source `
    $destination `
    /MIR `
    /XD "__pycache__" ".pytest_cache" `
    /XF "*.pyc"

$robocopyExitCode = $LASTEXITCODE

# Robocopy-codes 0 t/m 7 zijn succesvol.
if ($robocopyExitCode -gt 7) {
    throw "Robocopy is mislukt met foutcode $robocopyExitCode"
}

$sourceManifest = Join-Path $source "manifest.json"
$destinationManifest = Join-Path $destination "manifest.json"
if (-not (Test-Path -LiteralPath $destinationManifest)) {
    throw "Deploycontrole mislukt: manifest ontbreekt in $destinationManifest"
}

$sourceVersion = (Get-Content -LiteralPath $sourceManifest -Raw | ConvertFrom-Json).version
$destinationVersion = (
    Get-Content -LiteralPath $destinationManifest -Raw | ConvertFrom-Json
).version
if ($sourceVersion -ne $destinationVersion) {
    throw @"
Deploycontrole mislukt: de versies komen niet overeen.
Bron: $sourceVersion
Doel: $destinationVersion
"@
}

Write-Host "Niko Energie-dashboard installeren..."
& (Join-Path $PSScriptRoot "install_energy_dashboard.ps1") `
    -HomeAssistantConfig $HomeAssistantConfig

Write-Host ""
Write-Host "Deploy geslaagd."
Write-Host "Gecontroleerde versie: $destinationVersion"
Write-Host "Integratie geplaatst in:"
Write-Host "  $destination"
Write-Host ""
if ($previousDestinationVersion -eq $sourceVersion) {
    Write-Host "Alleen dashboardbestanden zijn bijgewerkt."
    Write-Host "Vernieuw het Niko Energie-dashboard; een herstart is niet nodig."
}
else {
    Write-Host "Controleer de configuratie en herstart Home Assistant volledig."
}
