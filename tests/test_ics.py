from datetime import datetime
from zoneinfo import ZoneInfo

from venueview.ics import (
    BLOCKED_EVENT_PROPERTIES,
    ALLOWED_EVENT_PROPERTIES,
    parse_ics,
    read_event_components,
)


def window():
    timezone = ZoneInfo("America/New_York")
    return (
        datetime(2026, 7, 17, tzinfo=timezone),
        datetime(2026, 7, 20, tzinfo=timezone),
    )


def test_parser_expands_recurrence_and_exdate(project_root):
    start, end = window()
    events = parse_ics(
        project_root / "data/synthetic/sample_calendar.ics",
        window_start=start,
        window_end=end,
    )

    assert len(events) == 8
    learn_to_skate = [event for event in events if event.title == "Community Learn to Skate"]
    assert [event.local_date.isoformat() for event in learn_to_skate] == [
        "2026-07-17",
        "2026-07-19",
    ]
    assert all(event.recurring for event in learn_to_skate)
    assert all(event.title != "Cancelled Synthetic Event" for event in events)


def test_multi_category_assignment_is_preserved(project_root):
    start, end = window()
    events = parse_ics(
        project_root / "data/synthetic/sample_calendar.ics",
        window_start=start,
        window_end=end,
    )
    meeting = next(
        event for event in events if event.title == "Community Planning Meeting"
    )

    assert meeting.categories == (
        "Summit Events Center > Level 2 > Harbor Hall A",
        "Summit Events Center > Level 2 > Harbor Hall B",
    )


def test_parser_whitelist_excludes_sensitive_property_types(project_root):
    components = read_event_components(
        project_root / "data/synthetic/sample_calendar.ics"
    )
    property_names = {name for component in components for name in component}

    assert property_names <= ALLOWED_EVENT_PROPERTIES
    assert property_names.isdisjoint(BLOCKED_EVENT_PROPERTIES)
