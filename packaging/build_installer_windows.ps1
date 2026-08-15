$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
  throw "The Windows installer must be built on Windows."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$iscc = $env:ISCC
if (-not $iscc) {
  $candidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
  )
  $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc -or -not (Test-Path $iscc)) {
  throw "Inno Setup 6 was not found. Install it or set ISCC to the full path of ISCC.exe."
}

if (-not (Test-Path "dist\VenueView\VenueView.exe")) {
  throw "Build the Windows bundle first with packaging\build_windows.ps1."
}

$venvRoot = if ($env:VENUEVIEW_BUILD_VENV) {
  $env:VENUEVIEW_BUILD_VENV
} else {
  Join-Path $projectRoot ".venv-build-windows"
}
$python = Join-Path $venvRoot "Scripts\python.exe"
if (-not (Test-Path $python)) {
  throw "The isolated Windows build environment is missing. Build the bundle first."
}
$version = & $python "packaging\release_info.py"
$edition = if ($env:VENUEVIEW_BUILD_EDITION) {
  $env:VENUEVIEW_BUILD_EDITION.ToLowerInvariant()
} else {
  "public"
}
if ($edition -eq "private") {
  $fileSuffix = "-Private"
  $outputDir = "..\..\dist\installer-private"
} elseif ($edition -eq "public") {
  $fileSuffix = ""
  $outputDir = "..\..\dist\installer"
} else {
  throw "VENUEVIEW_BUILD_EDITION must be public or private."
}

& $iscc "/DMyAppVersion=$version" "/DMyAppFileSuffix=$fileSuffix" "/DMyOutputDir=$outputDir" "packaging\installer\VenueView.iss"
Write-Host "Installer created in $outputDir."
