#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "The private macOS release must be built on macOS." >&2
  exit 1
fi

project_root="$(cd "$(dirname "$0")/.." && pwd)"
rules_source="${1:-${VENUEVIEW_PRIVATE_RULES_SOURCE:-}}"
if [[ -z "${rules_source}" ]]; then
  echo "Usage: bash packaging/build_private_release_macos.sh /private/path/rules.json" >&2
  exit 1
fi

rules_source="$(cd "$(dirname "${rules_source}")" && pwd)/$(basename "${rules_source}")"
if [[ ! -f "${rules_source}" ]]; then
  echo "The approved private operational rule pack was not found." >&2
  exit 1
fi
case "${rules_source}" in
  "${project_root}"|"${project_root}"/*)
    echo "Keep the private operational rule pack outside the VenueView project folder." >&2
    exit 1
    ;;
esac

export VENUEVIEW_BUILD_EDITION="private"
export VENUEVIEW_BUNDLED_PRIVATE_RULES="${rules_source}"
if [[ "${VENUEVIEW_PRODUCTION_RELEASE:-0}" == "1" ]]; then
  bash "${project_root}/packaging/build_production_release_macos.sh"
else
  bash "${project_root}/packaging/build_release_macos.sh"
fi

echo "Private VenueView release created in dist/installer-private/."
