param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$RulesPath
)

$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
  throw "The private Windows release must be built on Windows."
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedRules = (Resolve-Path $RulesPath -ErrorAction Stop).Path
if (-not (Test-Path $resolvedRules -PathType Leaf)) {
  throw "The approved private operational rule pack was not found."
}
$projectPrefix = $projectRoot.TrimEnd('\') + '\'
if ($resolvedRules.Equals($projectRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
    $resolvedRules.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Keep the private operational rule pack outside the VenueView project folder."
}

$env:VENUEVIEW_BUILD_EDITION = "private"
$env:VENUEVIEW_BUNDLED_PRIVATE_RULES = $resolvedRules
if ($env:VENUEVIEW_PRODUCTION_RELEASE -eq "1") {
  & "$PSScriptRoot\build_production_release_windows.ps1"
} else {
  & "$PSScriptRoot\build_release_windows.ps1"
}

Write-Host "Private VenueView release created in dist\installer-private\."
