from datetime import datetime
from zoneinfo import ZoneInfo

from venueview.combine import combine_events
from venueview.models import OperationalEvent
from venueview.rules import load_rule_pack


TIMEZONE = ZoneInfo("America/New_York")


def _event(
    source_uid: str,
    *,
    start: tuple[int, int],
    end: tuple[int, int],
    space: str,
    title: str = "Synthetic Hockey Session",
    group: str = "Synthetic Hockey Group",
    function: str = "Hockey",
) -> OperationalEvent:
    return OperationalEvent(
        source_uid=source_uid,
        title=title,
        start=datetime(2026, 7, 15, start[0], start[1], tzinfo=TIMEZONE),
        end=datetime(2026, 7, 15, end[0], end[1], tzinfo=TIMEZONE),
        category_path=f"North Arena > Sports > Rinks > {space}",
        venue="North Arena",
        space=space,
        group=group,
        function=function,
    )


def test_same_title_hockey_combines_despite_interleaved_other_rink(project_root):
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    events = [
        _event("synthetic-hockey-1", start=(8, 0), end=(9, 0), space="Rink B"),
        _event(
            "synthetic-other-rink",
            start=(8, 30),
            end=(9, 30),
            space="Rink C",
            title="Synthetic Figure Session",
            group="Synthetic Figure Group",
            function="Ice",
        ),
        _event("synthetic-hockey-2", start=(9, 10), end=(10, 0), space="Rink B"),
    ]

    combined = combine_events(events, rules)
    hockey = [event for event in combined if event.function == "Hockey"]

    assert len(hockey) == 1
    assert hockey[0].source_count == 2
    assert hockey[0].start.strftime("%H:%M") == "08:00"
    assert hockey[0].end.strftime("%H:%M") == "10:00"


def test_hockey_rule_respects_ten_minute_title_group_and_rink_boundaries(
    project_root,
):
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    events = [
        _event("synthetic-boundary-1", start=(8, 0), end=(9, 0), space="Rink C"),
        _event("synthetic-boundary-2", start=(9, 10), end=(10, 0), space="Rink C"),
        _event("synthetic-too-late", start=(10, 11), end=(11, 0), space="Rink C"),
        _event(
            "synthetic-other-title",
            start=(9, 10),
            end=(10, 0),
            space="Rink C",
            title="Different Synthetic Hockey Session",
        ),
        _event(
            "synthetic-other-group",
            start=(9, 10),
            end=(10, 0),
            space="Rink C",
            group="Different Synthetic Group",
        ),
        _event("synthetic-other-rink", start=(9, 10), end=(10, 0), space="Rink B"),
    ]

    combined = combine_events(events, rules)
    merged = [event for event in combined if event.source_count == 2]

    assert len(merged) == 1
    assert merged[0].space == "Rink C"
    assert merged[0].start.strftime("%H:%M") == "08:00"
    assert merged[0].end.strftime("%H:%M") == "10:00"


def test_different_event_in_same_rink_blocks_combination(project_root):
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    events = [
        _event("synthetic-blocked-1", start=(8, 0), end=(9, 0), space="Rink B"),
        _event(
            "synthetic-space-blocker",
            start=(9, 2),
            end=(9, 8),
            space="Rink B",
            title="Synthetic Maintenance Block",
            group="Operations",
            function="Maintenance",
        ),
        _event("synthetic-blocked-2", start=(9, 10), end=(10, 0), space="Rink B"),
    ]

    combined = combine_events(events, rules)
    hockey = [event for event in combined if event.function == "Hockey"]

    assert len(hockey) == 2
    assert all(event.source_count == 1 for event in hockey)


def test_generic_rule_combines_same_title_and_location_within_fifteen_minutes(
    project_root,
):
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    events = [
        _event(
            "synthetic-meeting-1",
            start=(8, 0),
            end=(9, 0),
            space="Meeting Room",
            title="Synthetic Operations Meeting",
            group="Synthetic Group",
            function="Meeting",
        ),
        _event(
            "synthetic-meeting-2",
            start=(9, 15),
            end=(10, 0),
            space="Meeting Room",
            title="Synthetic Operations Meeting",
            group="Synthetic Group",
            function="Meeting",
        ),
        _event(
            "synthetic-meeting-too-late",
            start=(10, 16),
            end=(11, 0),
            space="Meeting Room",
            title="Synthetic Operations Meeting",
            group="Synthetic Group",
            function="Meeting",
        ),
    ]
    for event in events:
        event.venue = "Summit Events Center"

    combined = combine_events(events, rules)

    assert len(combined) == 2
    assert combined[0].source_count == 2
    assert combined[0].start.strftime("%H:%M") == "08:00"
    assert combined[0].end.strftime("%H:%M") == "10:00"
    assert combined[1].source_count == 1
