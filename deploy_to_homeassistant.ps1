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

Write-Host "Source:"
Write-Host "  $source"

Write-Host "Destination:"
Write-Host "  $destination"

if (-not (Test-Path -LiteralPath $source)) {
    throw "The source directory does not exist: $source"
}

if (-not (Test-Path -LiteralPath $HomeAssistantConfig)) {
    throw @"
The Home Assistant Samba share is not accessible:

$HomeAssistantConfig

First open this path in Windows Explorer:
\\homeassistant\config

Sign in with the credentials configured in the Samba Share app.
If necessary, use the Home Assistant IP address instead of 'homeassistant'.
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

Write-Host "Copying integration..."

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

# Robocopy exit codes 0 through 7 indicate success.
if ($robocopyExitCode -gt 7) {
    throw "Robocopy failed with exit code $robocopyExitCode"
}

$sourceManifest = Join-Path $source "manifest.json"
$destinationManifest = Join-Path $destination "manifest.json"
if (-not (Test-Path -LiteralPath $destinationManifest)) {
    throw "Deployment validation failed: manifest is missing from $destinationManifest"
}

$sourceVersion = (Get-Content -LiteralPath $sourceManifest -Raw | ConvertFrom-Json).version
$destinationVersion = (
    Get-Content -LiteralPath $destinationManifest -Raw | ConvertFrom-Json
).version
if ($sourceVersion -ne $destinationVersion) {
    throw @"
Deployment validation failed: the versions do not match.
Source: $sourceVersion
Destination: $destinationVersion
"@
}

Write-Host "Installing the Niko Energy dashboard..."
& (Join-Path $PSScriptRoot "install_energy_dashboard.ps1") `
    -HomeAssistantConfig $HomeAssistantConfig

Write-Host ""
Write-Host "Deployment completed successfully."
Write-Host "Validated version: $destinationVersion"
Write-Host "Integration installed in:"
Write-Host "  $destination"
Write-Host ""
if ($previousDestinationVersion -eq $sourceVersion) {
    Write-Host "Only dashboard files were updated."
    Write-Host "Refresh the Niko Energy dashboard; no restart is required."
}
else {
    Write-Host "Validate the configuration and restart Home Assistant."
}
