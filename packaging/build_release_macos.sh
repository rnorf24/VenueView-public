#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "The macOS release must be built on macOS." >&2
  exit 1
fi

project_root="$(cd "$(dirname "$0")/.." && pwd)"
build_python="${VENUEVIEW_BUILD_VENV:-${project_root}/.venv-build-macos}/bin/python"
architecture="$(uname -m)"
edition="${VENUEVIEW_BUILD_EDITION:-public}"
if [[ "${edition}" != "public" && "${edition}" != "private" ]]; then
  echo "VENUEVIEW_BUILD_EDITION must be public or private." >&2
  exit 1
fi
rules_expectation="none"
installer_dir="dist/installer"
if [[ "${edition}" == "private" ]]; then
  rules_expectation="bundled"
  installer_dir="dist/installer-private"
fi

cd "${project_root}"
bash packaging/build_macos.sh
trust_status="unsigned-evaluation"
if [[ -n "${APPLE_APPLICATION_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp \
    --sign "${APPLE_APPLICATION_IDENTITY}" dist/VenueView.app
  codesign --verify --deep --strict --verbose=2 dist/VenueView.app
  trust_status="signed"
elif [[ "${VENUEVIEW_REQUIRE_SIGNING:-0}" == "1" ]]; then
  echo "APPLE_APPLICATION_IDENTITY is required for a production release." >&2
  exit 1
fi
"${build_python}" packaging/smoke_test_desktop.py \
  --expect-rules-source "${rules_expectation}" \
  dist/VenueView.app/Contents/MacOS/VenueView
PYTHON_BIN="${build_python}" bash packaging/build_installer_macos.sh
"${build_python}" packaging/write_release_manifest.py \
  --platform macOS \
  --architecture "${architecture}" \
  --edition "${edition}" \
  --trust-status "${trust_status}" \
  "${installer_dir}"

echo "VenueView macOS release passed its local health check."
if [[ "${trust_status}" == "unsigned-evaluation" ]]; then
  echo "Unsigned evaluation artifacts are in ${installer_dir}/."
else
  echo "Signed artifacts awaiting notarization are in ${installer_dir}/."
fi
