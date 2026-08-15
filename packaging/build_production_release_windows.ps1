$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
  throw "The production Windows release must be built on Windows."
}
if (-not $env:WINDOWS_CERT_THUMBPRINT -and -not $env:WINDOWS_CERT_PFX) {
  throw "Set WINDOWS_CERT_THUMBPRINT or WINDOWS_CERT_PFX before a production build."
}

$env:VENUEVIEW_REQUIRE_SIGNING = "1"
& "$PSScriptRoot\build_release_windows.ps1"

Write-Host "Production Windows release completed with verified Authenticode signatures and timestamping."
