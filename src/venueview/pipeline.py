from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .combine import combine_events
from .models import CalendarEvent, OperationalEvent, VenueProfile
from .profiles import category_leaf, category_root
from .rules import RulePack, classify_event, ignore_reason


@dataclass
class PipelineResult:
    detailed: list[OperationalEvent]
    combined: list[OperationalEvent]
    excluded_count: int
    unassigned_source_count: int


def _profile_rows(
    event: CalendarEvent, profile: VenueProfile
) -> list[OperationalEvent]:
    matching_paths = [
        path for path in event.categories if profile.includes_category(path)
    ]
    rows: list[OperationalEvent] = []
    for path in matching_paths:
        review_reasons: list[str] = []
        if not event.title.strip():
            review_reasons.append("Missing source title")
        if event.end <= event.start:
            review_reasons.append("End time is not later than start time")
        if event.status not in {"", "CONFIRMED"}:
            review_reasons.append(f"Source status: {event.status}")
        rows.append(
            OperationalEvent(
                source_uid=event.source_uid,
                title=event.title,
                start=event.start,
                end=event.end,
                category_path=path,
                venue=category_root(path),
                space=category_leaf(path),
                all_day=event.all_day,
                recurring=event.recurring,
                needs_review=review_reasons,
                locations=((category_root(path), category_leaf(path)),),
                source_row_keys=(
                    hashlib.sha256(
                        "\x1f".join(
                            (
                                event.source_uid,
                                event.start.isoformat(),
                                event.end.isoformat(),
                                path,
                            )
                        ).encode("utf-8")
                    ).hexdigest(),
                ),
            )
        )
    return rows


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def _group_multi_location_rows(
    events: list[OperationalEvent],
) -> list[OperationalEvent]:
    """Collapse one source occurrence expanded across several locations.

    Some calendar systems assign one occurrence to multiple categories or
    sub-calendars. VenueView normally preserves one operational row per matched
    location. This opt-in view keeps the occurrence as one event and presents
    its complete location set in a deterministic display value.
    """

    partitions: dict[
        tuple[str, object, object, str], list[OperationalEvent]
    ] = {}
    for event in events:
        key = (event.source_uid, event.start, event.end, _normalized(event.title))
        partitions.setdefault(key, []).append(event)

    grouped: list[OperationalEvent] = []
    for rows in partitions.values():
        if len(rows) == 1:
            grouped.append(rows[0])
            continue

        locations = sorted(
            {
                location
                for row in rows
                for location in (row.locations or ((row.venue, row.space),))
            },
            key=lambda location: (
                location[0].casefold(),
                location[1].casefold(),
            ),
        )
        if len(locations) == 1:
            grouped.append(rows[0])
            continue

        venues = list(dict.fromkeys(venue for venue, _space in locations))
        if len(venues) == 1:
            venue = venues[0]
            space = " / ".join(space for _venue, space in locations)
        else:
            venue = "Multiple venues"
            space = " / ".join(
                f"{location_venue} — {location_space}"
                for location_venue, location_space in locations
            )

        groups = list(dict.fromkeys(row.group for row in rows if row.group))
        functions = list(dict.fromkeys(row.function for row in rows if row.function))
        review_reasons = list(
            dict.fromkeys(reason for row in rows for reason in row.needs_review)
        )
        if len(groups) > 1:
            review_reasons.append(
                "Multi-location event has conflicting group classifications"
            )
        if len(functions) > 1:
            review_reasons.append(
                "Multi-location event has conflicting function classifications"
            )

        first = rows[0]
        grouped.append(
            first.clone(
                category_path=" | ".join(
                    dict.fromkeys(row.category_path for row in rows)
                ),
                venue=venue,
                space=space,
                group=" / ".join(groups),
                function=" / ".join(functions),
                needs_review=list(dict.fromkeys(review_reasons)),
                source_count=max(row.source_count for row in rows),
                applied_rules=list(
                    dict.fromkeys(
                        [
                            *(rule for row in rows for rule in row.applied_rules),
                            "group_multi_location_source_event",
                        ]
                    )
                ),
                locations=tuple(locations),
                source_row_keys=tuple(
                    dict.fromkeys(
                        key for row in rows for key in row.source_row_keys
                    )
                ),
            )
        )
    return grouped


def run_pipeline(
    events: list[CalendarEvent],
    profile: VenueProfile,
    rule_pack: RulePack,
    *,
    group_multi_location: bool = False,
) -> PipelineResult:
    detailed: list[OperationalEvent] = []
    excluded_count = 0
    unassigned_source_count = 0

    for source_event in events:
        rows = _profile_rows(source_event, profile)
        if not rows:
            unassigned_source_count += 1
            continue
        for row in rows:
            reason = ignore_reason(row, rule_pack)
            if reason:
                excluded_count += 1
                continue
            detailed.append(classify_event(row, rule_pack))

    if group_multi_location:
        detailed = _group_multi_location_rows(detailed)

    detailed.sort(
        key=lambda event: (
            event.start,
            event.venue.casefold(),
            event.space.casefold(),
            event.title.casefold(),
        )
    )
    return PipelineResult(
        detailed=detailed,
        combined=combine_events(detailed, rule_pack),
        excluded_count=excluded_count,
        unassigned_source_count=unassigned_source_count,
    )
