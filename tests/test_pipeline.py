import json
from datetime import datetime
from zoneinfo import ZoneInfo

from venueview.ics import parse_ics
from venueview.audit import operational_event_dict
from venueview.pipeline import run_pipeline
from venueview.profiles import load_profile
from venueview.rules import load_rule_pack


def load_events(project_root):
    timezone = ZoneInfo("America/New_York")
    return parse_ics(
        project_root / "data/synthetic/sample_calendar.ics",
        window_start=datetime(2026, 7, 17, tzinfo=timezone),
        window_end=datetime(2026, 7, 20, tzinfo=timezone),
    )


def test_profile_expands_one_source_event_into_each_selected_room(project_root):
    profile = load_profile(project_root / "config/profiles/summit_events_center.json")
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    result = run_pipeline(load_events(project_root), profile, rules)

    assert {event.space for event in result.detailed} == {"Harbor Hall A", "Harbor Hall B"}
    assert len(result.detailed) == 2


def test_opt_in_groups_one_striped_source_event_across_locations(project_root):
    profile = load_profile(project_root / "config/profiles/summit_events_center.json")
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    result = run_pipeline(
        load_events(project_root),
        profile,
        rules,
        group_multi_location=True,
    )

    assert len(result.detailed) == 1
    assert result.detailed[0].venue == "Summit Events Center"
    assert result.detailed[0].space == "Harbor Hall A / Harbor Hall B"
    assert result.detailed[0].source_count == 1
    assert result.detailed[0].locations == (
        ("Summit Events Center", "Harbor Hall A"),
        ("Summit Events Center", "Harbor Hall B"),
    )
    assert "group_multi_location_source_event" in result.detailed[0].applied_rules


def test_combination_respects_gap_and_rink_boundaries(project_root):
    profile = load_profile(project_root / "config/profiles/north_arena_rinks.json")
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    result = run_pipeline(load_events(project_root), profile, rules)

    assert len(result.detailed) == 6
    assert len(result.combined) == 5

    merged = [event for event in result.combined if event.source_count == 2]
    assert len(merged) == 1
    assert merged[0].space == "Rink A"
    assert merged[0].title == "Summit Skills Sessions"
    assert merged[0].start.strftime("%H:%M") == "07:00"
    assert merged[0].end.strftime("%H:%M") == "08:50"

    later_rink_a = [
        event
        for event in result.combined
        if event.space == "Rink A" and event.start.strftime("%H:%M") == "09:30"
    ]
    assert len(later_rink_a) == 1
    assert later_rink_a[0].source_count == 1
    assert later_rink_a[0].title == "Summit Skills Sessions"


def test_unclassified_rows_are_flagged_for_human_review(project_root):
    profile = load_profile(project_root / "config/profiles/summit_events_center.json")
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    result = run_pipeline(load_events(project_root), profile, rules)

    assert all(
        "Missing group classification" in event.needs_review
        for event in result.detailed
    )
    assert all(event.function == "Meeting" for event in result.detailed)


def test_combined_output_matches_golden_snapshot(project_root):
    profile = load_profile(project_root / "config/profiles/north_arena_rinks.json")
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    result = run_pipeline(load_events(project_root), profile, rules)
    expected = json.loads(
        (
            project_root / "data/synthetic/expected_north_arena_rinks_combined.json"
        ).read_text(encoding="utf-8")
    )

    assert [operational_event_dict(event) for event in result.combined] == expected
