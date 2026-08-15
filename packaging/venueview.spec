import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


spec_base = Path(SPECPATH).resolve()
project_root = spec_base if (spec_base / "src").is_dir() else spec_base.parent
config_root = project_root / "config"
public_config = [
    (str(config_root / "profiles"), "config/profiles"),
    (str(config_root / "rules" / "public_rules.json"), "config/rules"),
    (str(config_root / "venue_taxonomy.json"), "config"),
]
build_edition = os.environ.get("VENUEVIEW_BUILD_EDITION", "public").strip().lower()
private_rules_source = os.environ.get("VENUEVIEW_BUNDLED_PRIVATE_RULES", "").strip()
if build_edition not in {"public", "private"}:
    raise SystemExit("VENUEVIEW_BUILD_EDITION must be 'public' or 'private'.")
if build_edition == "private":
    if not private_rules_source:
        raise SystemExit(
            "Private builds require VENUEVIEW_BUNDLED_PRIVATE_RULES to point "
            "to an approved JSON rule pack outside the project."
        )
    private_rules_file = Path(private_rules_source).expanduser().resolve()
    if not private_rules_file.is_file():
        raise SystemExit("The requested private operational rule pack does not exist.")
    if private_rules_file == project_root or project_root in private_rules_file.parents:
        raise SystemExit(
            "The private operational rule pack must remain outside the project tree."
        )
    public_config.append(
        (str(private_rules_file), "config/operational_defaults")
    )
elif private_rules_source:
    raise SystemExit(
        "A bundled private rule pack may be supplied only for a private build."
    )
assets_root = project_root / "packaging" / "assets"
version_file = project_root / "packaging" / "generated" / "version_info.txt"

a = Analysis(
    [str(project_root / "packaging" / "venueview_entry.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=public_config,
    hiddenimports=(
        collect_submodules("flask")
        + collect_submodules("werkzeug")
        + collect_submodules("openpyxl")
        + collect_submodules("waitress")
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VenueView",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(assets_root / "venueview.ico"),
    version=str(version_file),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    name="VenueView",
)
