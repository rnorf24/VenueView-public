from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from .models import OperationalEvent
from .pipeline import PipelineResult


@dataclass(frozen=True)
class CombinationComponent:
    title: str
    start: datetime
    end: datetime
    venue: str
    space: str
    all_day: bool


@dataclass(frozen=True)
class CombinationReview:
    combination_id: str
    event: OperationalEvent
    components: tuple[CombinationComponent, ...]
    rule_ids: tuple[str, ...]


def combination_id(event: OperationalEvent) -> str:
    """Return a stable, non-source-revealing identifier for one combination."""

    if event.source_count <= 1 or len(event.source_row_keys) <= 1:
        return ""
    material = "\x1f".join(
        (
            event.local_date.isoformat(),
            event.venue.strip().casefold(),
            event.space.strip().casefold(),
            *sorted(event.source_row_keys),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _components_for_event(
    event: OperationalEvent, detailed: list[OperationalEvent]
) -> tuple[CombinationComponent, ...]:
    keys = set(event.source_row_keys)
    matching = [
        candidate
        for candidate in detailed
        if keys.intersection(candidate.source_row_keys)
    ]
    matching.sort(
        key=lambda candidate: (
            candidate.start,
            candidate.end,
            candidate.venue.casefold(),
            candidate.space.casefold(),
            candidate.title.casefold(),
        )
    )
    return tuple(
        CombinationComponent(
            title=candidate.title,
            start=candidate.start,
            end=candidate.end,
            venue=candidate.venue,
            space=candidate.space,
            all_day=candidate.all_day,
        )
        for candidate in matching
    )


def combination_reviews(result: PipelineResult) -> tuple[CombinationReview, ...]:
    reviews: list[CombinationReview] = []
    for event in result.combined:
        review_id = combination_id(event)
        if not review_id:
            continue
        reviews.append(
            CombinationReview(
                combination_id=review_id,
                event=event,
                components=_components_for_event(event, result.detailed),
                rule_ids=tuple(
                    rule_id
                    for rule_id in event.applied_rules
                    if rule_id.startswith("combine_")
                ),
            )
        )
    return tuple(reviews)


def apply_separation_overrides(
    result: PipelineResult, separate_ids: set[str]
) -> PipelineResult:
    """Replace selected combined events with their current detailed events."""

    if not separate_ids:
        return result

    output: list[OperationalEvent] = []
    for event in result.combined:
        review_id = combination_id(event)
        if not review_id or review_id not in separate_ids:
            output.append(event)
            continue
        keys = set(event.source_row_keys)
        output.extend(
            candidate.clone()
            for candidate in result.detailed
            if keys.intersection(candidate.source_row_keys)
        )

    output.sort(
        key=lambda event: (
            event.start,
            event.venue.casefold(),
            event.space.casefold(),
            event.title.casefold(),
        )
    )
    return PipelineResult(
        detailed=result.detailed,
        combined=output,
        excluded_count=result.excluded_count,
        unassigned_source_count=result.unassigned_source_count,
    )
