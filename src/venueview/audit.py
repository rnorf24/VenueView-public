from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .ics import BLOCKED_EVENT_PROPERTIES, parse_content_line, unfold_lines
from .models import CalendarEvent, OperationalEvent, VenueProfile
from .pipeline import PipelineResult


def inspect_property_schema(path: str | Path) -> dict[str, Any]:
    """Inspect property names and counts without reading their values into a report."""

    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    property_counts: Counter[str] = Counter()
    component_count = 0
    in_event = False
    for line in unfold_lines(text):
        marker = line.upper()
        if marker == "BEGIN:VEVENT":
            in_event = True
            component_count += 1
            continue
        if marker == "END:VEVENT":
            in_event = False
            continue
        if in_event and ":" in line:
            property_counts[parse_content_line(line).name] += 1
    return {
        "vevent_components": component_count,
        "property_presence": dict(sorted(property_counts.items())),
        "blocked_property_types_present": sorted(
            BLOCKED_EVENT_PROPERTIES.intersection(property_counts)
        ),
    }


def safe_audit_report(
    *,
    path: str | Path,
    events: list[CalendarEvent],
    profile: VenueProfile | None = None,
    pipeline_result: PipelineResult | None = None,
) -> dict[str, Any]:
    """Return aggregate structure only—never titles, UIDs, or source values."""

    schema = inspect_property_schema(path)
    roots = sorted(
        {
            path.split(">", 1)[0].strip()
            for event in events
            for path in event.categories
            if path.strip()
        }
    )
    spaces = sorted(
        {
            path.rsplit(">", 1)[-1].strip()
            for event in events
            for path in event.categories
            if ">" in path
        }
    )
    report: dict[str, Any] = {
        "privacy_mode": "safe-aggregate",
        "source_fingerprint": hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12],
        "window_occurrences": len(events),
        "recurring_occurrences": sum(event.recurring for event in events),
        "all_day_occurrences": sum(event.all_day for event in events),
        "multi_category_occurrences": sum(
            len(event.categories) > 1 for event in events
        ),
        "calendar_roots": roots,
        "discovered_spaces": spaces,
        **schema,
    }
    if profile:
        report["profile"] = {
            "profile_id": profile.profile_id,
            "name": profile.name,
            "pilot_status": profile.pilot_status,
        }
    if pipeline_result:
        report["pipeline"] = {
            "detailed_rows": len(pipeline_result.detailed),
            "combined_rows": len(pipeline_result.combined),
            "excluded_rows": pipeline_result.excluded_count,
            "source_occurrences_outside_profile": pipeline_result.unassigned_source_count,
            "rows_needing_review": sum(
                bool(event.needs_review) for event in pipeline_result.detailed
            ),
        }
    return report


def operational_event_dict(event: OperationalEvent) -> dict[str, Any]:
    """Serialize an operational row. This can contain sensitive source titles."""

    return {
        "date": event.local_date.isoformat(),
        "start": event.start.isoformat(),
        "end": event.end.isoformat(),
        "venue": event.venue,
        "space": event.space,
        "group": event.group,
        "function": event.function,
        "title": event.title,
        "needs_review": event.needs_review,
        "source_count": event.source_count,
        "applied_rules": event.applied_rules,
    }


SENSITIVE_TEXT_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "phone": re.compile(
        r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)"
    ),
    "agreement_reference": re.compile(
        r"\b(?:agreement|contract|docusign)\b", re.IGNORECASE
    ),
}


def scan_text_for_sensitive_patterns(text: str) -> list[str]:
    return sorted(
        name
        for name, pattern in SENSITIVE_TEXT_PATTERNS.items()
        if pattern.search(text)
    )
