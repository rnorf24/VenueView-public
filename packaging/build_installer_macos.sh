#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "The macOS installer image must be built on macOS." >&2
  exit 1
fi

if ! command -v pkgbuild >/dev/null 2>&1 || ! command -v hdiutil >/dev/null 2>&1; then
  echo "macOS installer artifacts require Apple's pkgbuild and hdiutil tools." >&2
  exit 1
fi

project_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
version="$("${python_bin}" "${project_root}/packaging/release_info.py")"
architecture="$(uname -m)"
edition="${VENUEVIEW_BUILD_EDITION:-public}"
case "${edition}" in
  public)
    filename_suffix=""
    output_name="installer"
    volume_name="VenueView"
    ;;
  private)
    filename_suffix="-Private"
    output_name="installer-private"
    volume_name="VenueView Private"
    ;;
  *)
    echo "VENUEVIEW_BUILD_EDITION must be public or private." >&2
    exit 1
    ;;
esac
app="${project_root}/dist/VenueView.app"
output="${project_root}/dist/${output_name}"
staging="$(mktemp -d "${TMPDIR:-/tmp}/venueview-dmg.XXXXXX")"
cleanup() {
  rm -rf "${staging}"
}
trap cleanup EXIT
if [[ ! -d "${app}" ]]; then
  echo "Build dist/VenueView.app first with packaging/build_macos.sh." >&2
  exit 1
fi

mkdir -p "${output}"
pkg_args=(
  --component "${app}"
  --install-location "/Applications"
)
if [[ -n "${APPLE_INSTALLER_IDENTITY:-}" ]]; then
  pkg_args+=(--sign "${APPLE_INSTALLER_IDENTITY}")
elif [[ "${VENUEVIEW_REQUIRE_SIGNING:-0}" == "1" ]]; then
  echo "APPLE_INSTALLER_IDENTITY is required for a production release." >&2
  exit 1
fi
pkgbuild "${pkg_args[@]}" \
  "${output}/VenueView-${version}${filename_suffix}-macOS-${architecture}.pkg"
ditto "${app}" "${staging}/VenueView.app"
ln -s /Applications "${staging}/Applications"
hdiutil create \
  -volname "${volume_name}" \
  -srcfolder "${staging}" \
  -ov \
  -format UDZO \
  "${output}/VenueView-${version}${filename_suffix}-macOS-${architecture}.dmg"
echo "Installer image created in dist/${output_name}."
