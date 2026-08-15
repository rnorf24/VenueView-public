$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
  throw "The Windows bundle must be built on Windows."
}

Write-Host "Building VenueView for Windows..."
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$venvRoot = if ($env:VENUEVIEW_BUILD_VENV) {
  $env:VENUEVIEW_BUILD_VENV
} else {
  Join-Path $projectRoot ".venv-build-windows"
}
$python = Join-Path $venvRoot "Scripts\python.exe"
if (-not (Test-Path $python)) {
  Write-Host "Creating the isolated build environment..."
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m venv $venvRoot
  } else {
    python -m venv $venvRoot
  }
}

& $python -m pip install --disable-pip-version-check ".[build]"
& $python packaging\generate_windows_version.py
& $python -m PyInstaller --noconfirm --clean packaging/venueview.spec

Write-Host "Build complete: dist/VenueView/VenueView.exe"
Write-Host "The bundle includes Python and does not require Python on the user's computer."
Write-Host "Code signing and the Windows installer are separate release steps."
