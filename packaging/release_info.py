from __future__ import annotations

import argparse
import re
from pathlib import Path


SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:[-+][0-9A-Za-z.-]+)?$"
)


def read_project_version(pyproject_path: Path) -> str:
    """Read the project version without requiring a TOML dependency."""

    in_project = False
    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "[project]":
            in_project = True
            continue
        if in_project and line.startswith("["):
            break
        if in_project:
            match = re.fullmatch(r'version\s*=\s*"([^"]+)"', line)
            if match:
                version = match.group(1)
                if not SEMVER_PATTERN.fullmatch(version):
                    raise ValueError(f"Project version is not semantic: {version}")
                return version
    raise ValueError(f"No [project] version found in {pyproject_path}")


def numeric_version(version: str) -> tuple[int, int, int, int]:
    match = SEMVER_PATTERN.fullmatch(version)
    if not match:
        raise ValueError(f"Project version is not semantic: {version}")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        0,
    )


def validate_tag(tag: str, version: str) -> None:
    normalized = tag.removeprefix("refs/tags/")
    expected = f"v{version}"
    if normalized != expected:
        raise ValueError(
            f"Release tag {normalized!r} does not match project version {expected!r}."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read VenueView release metadata")
    parser.add_argument("--check-tag")
    args = parser.parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    version = read_project_version(project_root / "pyproject.toml")
    if args.check_tag:
        validate_tag(args.check_tag, version)
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
