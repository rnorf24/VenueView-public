from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

from .rules import RulePack, load_rule_pack


PRIVATE_RULES_FILENAME = "private_rules.json"
BUNDLED_RULES_DIRECTORY = "operational_defaults"
MAX_PRIVATE_RULE_PACK_BYTES = 1024 * 1024


def default_private_rules_path() -> Path:
    """Return a per-user path outside the app bundle and source repository."""

    configured = os.environ.get("VENUEVIEW_PRIVATE_RULES_PATH")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        root = Path(
            os.environ.get("APPDATA")
            or os.environ.get("LOCALAPPDATA")
            or Path.home() / "AppData" / "Roaming"
        )
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "VenueView" / PRIVATE_RULES_FILENAME


def bundled_private_rules_path(config_root: str | Path) -> Path | None:
    """Return the one private-edition default pack, when the bundle has one.

    Public builds omit ``config/operational_defaults`` entirely. Private builds
    add exactly one validated JSON file to that directory at packaging time.
    The source file remains outside the source tree and repository.
    """

    directory = Path(config_root) / BUNDLED_RULES_DIRECTORY
    if not directory.is_dir():
        return None
    candidates = sorted(path for path in directory.glob("*.json") if path.is_file())
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError(
            "The private application bundle must contain exactly one operational "
            "rule pack."
        )
    return candidates[0]


def load_optional_private_rule_pack(path: str | Path) -> RulePack | None:
    candidate = Path(path)
    if not candidate.is_file():
        return None
    if candidate.stat().st_size > MAX_PRIVATE_RULE_PACK_BYTES:
        raise ValueError("Saved operational rule pack exceeds the 1 MB limit.")
    return load_rule_pack(candidate)


def persist_private_rule_pack(path: str | Path, text: str) -> None:
    """Atomically store an already-validated rule pack with private permissions."""

    encoded = text.encode("utf-8")
    if len(encoded) > MAX_PRIVATE_RULE_PACK_BYTES:
        raise ValueError("Operational rule pack exceeds the 1 MB limit.")

    destination = Path(path)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        destination.parent.chmod(0o700)
    except OSError:
        pass

    temporary = destination.with_name(
        f".{destination.name}.{secrets.token_hex(8)}.tmp"
    )
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def remove_private_rule_pack(path: str | Path) -> None:
    """Remove only the saved per-user replacement pack, when one exists."""

    candidate = Path(path)
    if candidate.exists() and not candidate.is_file():
        raise OSError("The saved operational settings path is not a file.")
    candidate.unlink(missing_ok=True)
