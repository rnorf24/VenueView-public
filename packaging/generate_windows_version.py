from __future__ import annotations

import argparse
from pathlib import Path

from release_info import numeric_version, read_project_version


TEMPLATE = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric_version},
    prodvers={numeric_version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'VenueView'),
          StringStruct('FileDescription', 'VenueView local calendar processing'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'VenueView'),
          StringStruct('OriginalFilename', 'VenueView.exe'),
          StringStruct('ProductName', 'VenueView'),
          StringStruct('ProductVersion', '{version}'),
        ],
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Windows version metadata")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    version = read_project_version(project_root / "pyproject.toml")
    output = args.output or project_root / "packaging/generated/version_info.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        TEMPLATE.format(version=version, numeric_version=numeric_version(version)),
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
