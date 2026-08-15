from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from .models import OperationalEvent
from .rules import CombinationRule, RulePack, event_field, rule_matches


def _partition_key(event: OperationalEvent, rule: CombinationRule) -> tuple[str, ...]:
    return tuple(
        " ".join(event_field(event, field_name).split()).casefold()
        for field_name in rule.partition_by
    )


def _same_space(left: OperationalEvent, right: OperationalEvent) -> bool:
    left_locations = set(left.locations or ((left.venue, left.space),))
    right_locations = set(right.locations or ((right.venue, right.space),))
    return (
        left.local_date == right.local_date
        and bool(
            {
                (venue.strip().casefold(), space.strip().casefold())
                for venue, space in left_locations
            }
            & {
                (venue.strip().casefold(), space.strip().casefold())
                for venue, space in right_locations
            }
        )
    )


def _has_intervening_space_blocker(
    all_events: list[OperationalEvent],
    current: OperationalEvent,
    following: OperationalEvent,
    rule: CombinationRule,
) -> bool:
    """Return true when another event occupies the same space during the gap."""

    if following.start <= current.end:
        return False
    current_partition = _partition_key(current, rule)
    return any(
        _same_space(candidate, current)
        and _partition_key(candidate, rule) != current_partition
        and candidate.start < following.start
        and candidate.end > current.end
        for candidate in all_events
    )


def _merge(
    current: OperationalEvent, following: OperationalEvent, rule: CombinationRule
) -> OperationalEvent:
    current.end = max(current.end, following.end)
    current.start = min(current.start, following.start)
    current.source_count += following.source_count
    review_reasons = current.needs_review + following.needs_review
    if (
        current.group
        and following.group
        and current.group.strip().casefold() != following.group.strip().casefold()
    ):
        review_reasons.append("Combined events have conflicting group classifications")
    if (
        current.function
        and following.function
        and current.function.strip().casefold()
        != following.function.strip().casefold()
    ):
        review_reasons.append(
            "Combined events have conflicting function classifications"
        )
    current.needs_review = list(dict.fromkeys(review_reasons))
    current.applied_rules = list(
        dict.fromkeys(current.applied_rules + following.applied_rules + [rule.rule_id])
    )
    if rule.result.get("title"):
        current.title = rule.result["title"]
    if rule.result.get("group"):
        current.group = rule.result["group"]
    if rule.result.get("function"):
        current.function = rule.result["function"]
    current.locations = tuple(
        dict.fromkeys(
            (
                current.locations or ((current.venue, current.space),)
            )
            + (
                following.locations or ((following.venue, following.space),)
            )
        )
    )
    current.source_row_keys = tuple(
        dict.fromkeys(current.source_row_keys + following.source_row_keys)
    )
    return current


def _finalize(current: OperationalEvent, rule: CombinationRule) -> OperationalEvent:
    if rule.result.get("title"):
        current.title = rule.result["title"]
    if rule.result.get("group"):
        current.group = rule.result["group"]
    if rule.result.get("function"):
        current.function = rule.result["function"]
    # A result-bearing rule may normalize even a single matched occurrence.
    # An empty-result adjacency rule has done nothing unless _merge recorded it.
    if rule.result and rule.rule_id not in current.applied_rules:
        current.applied_rules.append(rule.rule_id)
    return current


def combine_events(
    events: list[OperationalEvent], rule_pack: RulePack
) -> list[OperationalEvent]:
    """Combine only events matched by an explicit, enabled combination rule."""

    assigned: defaultdict[str, list[OperationalEvent]] = defaultdict(list)
    unmatched: list[OperationalEvent] = []
    rule_lookup = {
        rule.rule_id: rule for rule in rule_pack.combination_rules if rule.enabled
    }
    for event in events:
        matching_rule = next(
            (
                rule
                for rule in rule_pack.combination_rules
                if rule.enabled and rule_matches(event, rule.conditions)
            ),
            None,
        )
        if matching_rule is None:
            unmatched.append(event.clone())
        else:
            assigned[matching_rule.rule_id].append(event.clone())

    output = unmatched
    for rule_id, matched_events in assigned.items():
        rule = rule_lookup[rule_id]
        partitions: defaultdict[tuple[str, ...], list[OperationalEvent]] = defaultdict(
            list
        )
        for event in matched_events:
            partitions[_partition_key(event, rule)].append(event)

        for partition_events in partitions.values():
            partition_events.sort(
                key=lambda event: (event.start, event.end, event.title.casefold())
            )
            current: OperationalEvent | None = None
            for event in partition_events:
                if current is None:
                    current = event
                    continue
                gap = event.start - current.end
                same_day = event.local_date == current.local_date
                if (
                    same_day
                    and gap <= timedelta(minutes=rule.max_gap_minutes)
                    and not _has_intervening_space_blocker(events, current, event, rule)
                ):
                    current = _merge(current, event, rule)
                else:
                    output.append(_finalize(current, rule))
                    current = event
            if current is not None:
                output.append(_finalize(current, rule))

    return sorted(
        output,
        key=lambda event: (
            event.start,
            event.venue.casefold(),
            event.space.casefold(),
            event.title.casefold(),
        ),
    )
