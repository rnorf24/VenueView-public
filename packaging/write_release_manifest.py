from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from release_info import read_project_version


MANIFEST_NAMES = {"release-manifest.json", "SHA256SUMS.txt"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write desktop release checksums")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--edition", choices=("public", "private"), default="public")
    parser.add_argument(
        "--trust-status",
        choices=("unsigned-evaluation", "signed", "signed-and-notarized", "signed-and-timestamped"),
        default="unsigned-evaluation",
    )
    args = parser.parse_args(argv)
    directory = args.directory.resolve()
    project_root = Path(__file__).resolve().parents[1]
    version = read_project_version(project_root / "pyproject.toml")
    artifacts = [
        path
        for path in sorted(directory.iterdir())
        if path.is_file()
        and path.name not in MANIFEST_NAMES
        and version in path.name
    ]
    if not artifacts:
        parser.error(f"No release artifacts found in {directory}")

    records = [
        {
            "filename": path.name,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in artifacts
    ]
    (directory / "release-manifest.json").write_text(
        json.dumps(
            {
                "product": "VenueView",
                "version": version,
                "platform": args.platform,
                "architecture": args.architecture,
                "edition": args.edition,
                "trust_status": args.trust_status,
                "artifacts": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (directory / "SHA256SUMS.txt").write_text(
        "".join(f"{record['sha256']}  {record['filename']}\n" for record in records),
        encoding="utf-8",
    )
    print(f"Release manifest written for {len(records)} artifact(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
