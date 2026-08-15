$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
  throw "The Windows release must be built on Windows."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvRoot = if ($env:VENUEVIEW_BUILD_VENV) {
  $env:VENUEVIEW_BUILD_VENV
} else {
  Join-Path $projectRoot ".venv-build-windows"
}
$python = Join-Path $venvRoot "Scripts\python.exe"
$edition = if ($env:VENUEVIEW_BUILD_EDITION) {
  $env:VENUEVIEW_BUILD_EDITION.ToLowerInvariant()
} else {
  "public"
}
if ($edition -notin @("public", "private")) {
  throw "VENUEVIEW_BUILD_EDITION must be public or private."
}
$rulesExpectation = if ($edition -eq "private") { "bundled" } else { "none" }
$installerDir = if ($edition -eq "private") {
  "dist\installer-private"
} else {
  "dist\installer"
}

Set-Location $projectRoot
& "$PSScriptRoot\build_windows.ps1"
if ($env:VENUEVIEW_REQUIRE_SIGNING -eq "1") {
  & "$PSScriptRoot\sign_windows_artifact.ps1" "dist\VenueView\VenueView.exe"
}
& $python packaging\smoke_test_desktop.py `
  --expect-rules-source $rulesExpectation `
  dist\VenueView\VenueView.exe
& "$PSScriptRoot\build_installer_windows.ps1"
$trustStatus = "unsigned-evaluation"
if ($env:VENUEVIEW_REQUIRE_SIGNING -eq "1") {
  $version = & $python packaging\release_info.py
  $suffix = if ($edition -eq "private") { "-Private" } else { "" }
  $installer = Join-Path $installerDir "VenueView-$version$suffix-Windows-x64-Setup.exe"
  & "$PSScriptRoot\sign_windows_artifact.ps1" $installer
  $trustStatus = "signed-and-timestamped"
}
& $python packaging\write_release_manifest.py `
  --platform Windows `
  --architecture $env:PROCESSOR_ARCHITECTURE `
  --edition $edition `
  --trust-status $trustStatus `
  $installerDir

Write-Host "VenueView Windows release passed its local health check."
if ($trustStatus -eq "unsigned-evaluation") {
  Write-Host "Unsigned evaluation artifacts are in $installerDir\."
} else {
  Write-Host "Signed and timestamped artifacts are in $installerDir\."
}
