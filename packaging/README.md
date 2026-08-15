# VenueView Packaging

This folder contains bundled-runtime build paths for Windows and macOS. Both
packages include Python, VenueView Core, Flask, Waitress, the Excel-writing
dependency, and public configuration so an end user does not install Python
separately.

Public packaging is the default. It never contains an operational private rule
pack. An approved internal private build is created only with the explicit
private wrapper and a rules file stored outside this project.

## Approved private release builds

Private builds automatically activate the supplied standard operational rules.
The installed interface retains **Import or replace rules**; an imported file is
stored in per-user application data and takes precedence over the built-in pack.

On macOS, from the project root:

```bash
bash packaging/build_private_release_macos.sh "/private/path/VenueView_Private_Operational_Rules.json"
```

On Windows, from the project root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\packaging\build_private_release_windows.ps1 "C:\private\path\VenueView_Private_Operational_Rules.json"
```

The private artifacts are written to `dist/installer-private/` and include
`Private` in their filenames. Keep that directory access-controlled and never
upload its contents to the public GitHub release. The wrapper rejects a private
rules source stored inside the VenueView project folder.

These commands intentionally create unsigned evaluation builds unless the
production mode described below is explicitly selected.

## Production signing and notarization

Production wrappers fail closed when the required signing credentials are not
available. Do not store certificates, passwords, notary credentials, or private
operational rules in this repository.

For a public macOS production build, provide the keychain identity names and a
`notarytool` keychain profile, then run:

```bash
export APPLE_APPLICATION_IDENTITY="Developer ID Application: Approved Publisher (TEAMID)"
export APPLE_INSTALLER_IDENTITY="Developer ID Installer: Approved Publisher (TEAMID)"
export APPLE_NOTARY_PROFILE="venueview-notary"
bash packaging/build_production_release_macos.sh
```

For the internal private edition, use the existing private wrapper with
production mode enabled:

```bash
VENUEVIEW_PRODUCTION_RELEASE=1 \
  bash packaging/build_private_release_macos.sh "/private/path/VenueView_Private_Operational_Rules.json"
```

The production path signs the app with the hardened runtime, signs the PKG,
submits both DMG and PKG for notarization, staples and validates the tickets,
checks Gatekeeper assessment, and records `signed-and-notarized` only after all
commands succeed.

For Windows, install the Windows SDK signing tools and configure either a
certificate-store thumbprint or a protected PFX path. A timestamp URL defaults
to DigiCert and can be changed with `WINDOWS_TIMESTAMP_URL`:

```powershell
$env:WINDOWS_CERT_THUMBPRINT = "APPROVED_CERTIFICATE_THUMBPRINT"
.\packaging\build_production_release_windows.ps1
```

For the internal private edition:

```powershell
$env:VENUEVIEW_PRODUCTION_RELEASE = "1"
$env:WINDOWS_CERT_THUMBPRINT = "APPROVED_CERTIFICATE_THUMBPRINT"
.\packaging\build_private_release_windows.ps1 "C:\private\path\VenueView_Private_Operational_Rules.json"
```

The Windows production path signs and verifies the bundled executable before
packaging, then signs, timestamps, and verifies the final installer. Its
manifest records `signed-and-timestamped` only after both validations succeed.

## Recommended Windows release build

From the project root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\packaging\build_release_windows.ps1
```

Install Inno Setup 6 before running the command. The release script creates an
isolated `.venv-build-windows` environment, builds `dist/VenueView/`, launches
`VenueView.exe` on a temporary loopback port, verifies `/health`, creates the
setup executable, and writes release checksums under `dist/installer/`.

For diagnosis, the bundle and installer steps can still be run individually:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\packaging\build_windows.ps1
.\packaging\build_installer_windows.ps1
```

The optional `ISCC` environment variable can point to a non-default Inno Setup
installation. The installer is intentionally a separate step from the bundle
so the one-folder output can be scanned and tested first.

## Recommended macOS release build

From the project root in Terminal on a Mac:

```bash
bash packaging/build_release_macos.sh
```

The release script creates an isolated `.venv-build-macos` environment, builds
`dist/VenueView.app`, launches its bundled executable on a temporary loopback
port, verifies `/health`, creates the PKG and DMG, and writes release checksums
under `dist/installer/`.

For diagnosis, the app and installer steps can still be run individually:

```bash
bash packaging/build_macos.sh
bash packaging/build_installer_macos.sh
```

The build targets the architecture of the Python interpreter used to build it:
Apple Silicon (`arm64`) or Intel (`x86_64`). Build and test each required
architecture separately. A `universal2` release can be evaluated later if the
selected Python distribution and every binary dependency support it.

PyInstaller is not a cross-platform compiler. Run the Windows build on Windows
and the macOS build on macOS.

## GitHub evaluation builds

The **Desktop Builds** workflow can be started manually from the repository's
Actions tab. It also runs for tags such as `v1.0.0-rc.3`; a tag build fails if the tag
does not match the version in `pyproject.toml`. The workflow builds natively on
Windows and macOS, runs the same executable health smoke check, and uploads the
installer directory as an unsigned evaluation artifact.

`SHA256SUMS.txt` and `release-manifest.json` let a tester verify that an artifact
was transferred without accidental modification. They do not establish who
published it. The manifest also records whether the artifact is an unsigned
evaluation, signed, signed-and-notarized, or signed-and-timestamped build. That
field is written by the corresponding release workflow; clean-machine testing
and organizational approval remain separate requirements.

## Local service boundary

The packaged UI runs a local Waitress service bound only to `127.0.0.1` (or
explicitly `localhost`). Port `0` is the default, so the operating system
selects an available loopback port and VenueView prints the exact local URL
before opening the browser. A fixed port can be requested for troubleshooting,
for example `VenueView.exe --port 8765`, but a wildcard host such as
`0.0.0.0` is rejected.

## Why one-folder first

One-folder builds are easier to inspect, diagnose, update, and scan with an
organization’s endpoint security tools. A one-file installer can be considered
after the pilot workflow is stable.

## Release requirements before staff distribution

- Build on each target operating system and architecture.
- Test on clean Windows and macOS accounts without Python installed.
- Test local-only binding and source-file handling.
- Confirm generated files open correctly in the available spreadsheet software.
- Add Windows code signing if required by organizational IT policy.
- Sign the Mac app with an approved Apple Developer ID and notarize the release
  before broad distribution.
- Build and test the platform installer after the one-folder bundle is stable.
- Document installer upgrade and uninstall procedures per platform.
- Add a rollback procedure for rule-pack changes.
- Never bundle real calendar exports or private source data.

The current macOS bundle identifier, `com.venueview.desktop`, is a development
identifier. Replace it only after the organization approves the production
identity and signing owner.
