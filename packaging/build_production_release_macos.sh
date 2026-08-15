#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "The production macOS release must be built on macOS." >&2
  exit 1
fi

: "${APPLE_APPLICATION_IDENTITY:?Set APPLE_APPLICATION_IDENTITY to the Developer ID Application identity.}"
: "${APPLE_INSTALLER_IDENTITY:?Set APPLE_INSTALLER_IDENTITY to the Developer ID Installer identity.}"
: "${APPLE_NOTARY_PROFILE:?Set APPLE_NOTARY_PROFILE to a keychain profile created with notarytool.}"

project_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="${VENUEVIEW_BUILD_VENV:-${project_root}/.venv-build-macos}/bin/python"
edition="${VENUEVIEW_BUILD_EDITION:-public}"
installer_dir="${project_root}/dist/installer"
suffix=""
if [[ "${edition}" == "private" ]]; then
  installer_dir="${project_root}/dist/installer-private"
  suffix="-Private"
fi

export VENUEVIEW_REQUIRE_SIGNING=1
bash "${project_root}/packaging/build_release_macos.sh"

version="$("${python_bin}" "${project_root}/packaging/release_info.py")"
architecture="$(uname -m)"
dmg="${installer_dir}/VenueView-${version}${suffix}-macOS-${architecture}.dmg"
pkg="${installer_dir}/VenueView-${version}${suffix}-macOS-${architecture}.pkg"

xcrun notarytool submit "${dmg}" --keychain-profile "${APPLE_NOTARY_PROFILE}" --wait
xcrun stapler staple "${dmg}"
xcrun stapler validate "${dmg}"
xcrun notarytool submit "${pkg}" --keychain-profile "${APPLE_NOTARY_PROFILE}" --wait
xcrun stapler staple "${pkg}"
xcrun stapler validate "${pkg}"
spctl --assess --type execute --verbose=2 "${project_root}/dist/VenueView.app"
spctl --assess --type install --verbose=2 "${pkg}"

"${python_bin}" "${project_root}/packaging/write_release_manifest.py" \
  --platform macOS \
  --architecture "${architecture}" \
  --edition "${edition}" \
  --trust-status signed-and-notarized \
  "${installer_dir}"

echo "Production macOS release completed with verified signatures and notarization."
