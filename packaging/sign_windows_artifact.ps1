param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$ArtifactPath
)

$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
  throw "Windows artifacts must be signed on Windows."
}

$artifact = (Resolve-Path $ArtifactPath -ErrorAction Stop).Path
$signtool = $env:SIGNTOOL
if (-not $signtool) {
  $kitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
  if (Test-Path $kitsRoot) {
    $signtool = Get-ChildItem $kitsRoot -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
      Sort-Object FullName -Descending |
      Select-Object -First 1 -ExpandProperty FullName
  }
}
if (-not $signtool -or -not (Test-Path $signtool)) {
  throw "signtool.exe was not found. Install the Windows SDK or set SIGNTOOL to its full path."
}

$timestampUrl = if ($env:WINDOWS_TIMESTAMP_URL) {
  $env:WINDOWS_TIMESTAMP_URL
} else {
  "http://timestamp.digicert.com"
}

$signArguments = @("sign", "/fd", "SHA256", "/tr", $timestampUrl, "/td", "SHA256")
if ($env:WINDOWS_CERT_THUMBPRINT) {
  $signArguments += @("/sha1", $env:WINDOWS_CERT_THUMBPRINT)
} elseif ($env:WINDOWS_CERT_PFX) {
  $pfx = (Resolve-Path $env:WINDOWS_CERT_PFX -ErrorAction Stop).Path
  $signArguments += @("/f", $pfx)
  if ($env:WINDOWS_CERT_PASSWORD) {
    $signArguments += @("/p", $env:WINDOWS_CERT_PASSWORD)
  }
} else {
  throw "Set WINDOWS_CERT_THUMBPRINT or WINDOWS_CERT_PFX before a production build."
}
$signArguments += $artifact

& $signtool @signArguments
if ($LASTEXITCODE -ne 0) {
  throw "Authenticode signing failed for $artifact."
}
& $signtool verify /pa /v $artifact
if ($LASTEXITCODE -ne 0) {
  throw "Authenticode verification failed for $artifact."
}
