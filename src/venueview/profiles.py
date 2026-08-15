from __future__ import annotations

import json
from pathlib import Path

from .models import VenueProfile


def load_profile(path: str | Path) -> VenueProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"profile_id", "name", "category_prefixes"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"Profile is missing required keys: {', '.join(missing)}")
    return VenueProfile(
        profile_id=str(data["profile_id"]),
        name=str(data["name"]),
        category_prefixes=tuple(str(value) for value in data["category_prefixes"]),
        excluded_category_prefixes=tuple(
            str(value) for value in data.get("excluded_category_prefixes", [])
        ),
        allowed_spaces=tuple(str(value) for value in data.get("allowed_spaces", [])),
        output_modes=tuple(
            str(value)
            for value in data.get("output_modes", ["detailed", "combined", "both"])
        ),
        pilot_status=str(data.get("pilot_status", "discovered")),
    )


def category_root(category_path: str) -> str:
    return category_path.split(">", 1)[0].strip()


def category_leaf(category_path: str) -> str:
    return category_path.rsplit(">", 1)[-1].strip()
