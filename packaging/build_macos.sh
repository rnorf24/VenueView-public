#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "VenueView.app must be built on macOS."
  exit 1
fi

project_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
architecture="$(uname -m)"
asset_dir="${project_root}/packaging/assets"
build_venv="${VENUEVIEW_BUILD_VENV:-${project_root}/.venv-build-macos}"
build_python="${build_venv}/bin/python"
iconset_dir="$(mktemp -d "${TMPDIR:-/tmp}/venueview-iconset.XXXXXX")/VenueView.iconset"

cleanup_iconset() {
  rm -r "$(dirname "${iconset_dir}")"
}
trap cleanup_iconset EXIT

if ! command -v sips >/dev/null 2>&1 || ! command -v iconutil >/dev/null 2>&1; then
  echo "macOS builds require Apple's sips and iconutil tools." >&2
  exit 1
fi

mkdir -p "${iconset_dir}"
for size in 16 32 128 256 512; do
  sips -z "${size}" "${size}" "${asset_dir}/venueview.png" --out "${iconset_dir}/icon_${size}x${size}.png" >/dev/null
  retina=$((size * 2))
  sips -z "${retina}" "${retina}" "${asset_dir}/venueview.png" --out "${iconset_dir}/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "${iconset_dir}" -o "${asset_dir}/venueview.icns"

echo "Building VenueView for macOS (${architecture})..."
cd "${project_root}"
if [[ ! -x "${build_python}" ]]; then
  "${python_bin}" -m venv "${build_venv}"
fi
"${build_python}" -m pip install --disable-pip-version-check ".[build]"
"${build_python}" -m PyInstaller --noconfirm --clean packaging/venueview_macos.spec

echo "Build complete: dist/VenueView.app"
echo "This build targets ${architecture}. Test on a clean Mac without Python installed."
echo "Developer ID signing and Apple notarization are separate release tasks."
