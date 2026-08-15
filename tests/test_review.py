from datetime import datetime
from zoneinfo import ZoneInfo

from venueview.ics import parse_ics
from venueview.pipeline import run_pipeline
from venueview.profiles import load_profile
from venueview.review import apply_separation_overrides, combination_reviews
from venueview.rules import load_rule_pack


def _pipeline(project_root):
    timezone = ZoneInfo("America/New_York")
    events = parse_ics(
        project_root / "data/synthetic/sample_calendar.ics",
        window_start=datetime(2026, 7, 17, tzinfo=timezone),
        window_end=datetime(2026, 7, 20, tzinfo=timezone),
    )
    profile = load_profile(
        project_root / "config/profiles/north_arena_rinks.json"
    )
    rules = load_rule_pack(project_root / "config/rules/public_rules.json")
    return run_pipeline(events, profile, rules)


def test_combination_review_preserves_source_schedule_without_source_uid(project_root):
    result = _pipeline(project_root)
    reviews = combination_reviews(result)

    assert len(reviews) == 1
    review = reviews[0]
    assert len(review.combination_id) == 24
    assert review.event.title == "Summit Skills Sessions"
    assert [component.title for component in review.components] == [
        "Summit Skills - Open",
        "Summit Skills - Advanced",
    ]
    assert [component.start.strftime("%H:%M") for component in review.components] == [
        "07:00",
        "08:00",
    ]
    assert all("venueview-synthetic" not in key for key in review.event.source_row_keys)


def test_separation_override_restores_component_events(project_root):
    result = _pipeline(project_root)
    review = combination_reviews(result)[0]
    separated = apply_separation_overrides(result, {review.combination_id})

    assert len(result.combined) == 5
    assert len(separated.combined) == 6
    assert not any(event.source_count > 1 for event in separated.combined)
    assert [
        event.title
        for event in separated.combined
        if event.space == "Rink A"
        and event.start.strftime("%H:%M") in {"07:00", "08:00"}
    ] == ["Summit Skills - Open", "Summit Skills - Advanced"]


def test_unknown_override_does_not_change_output(project_root):
    result = _pipeline(project_root)
    unchanged = apply_separation_overrides(result, {"not-a-current-review"})

    assert [event.title for event in unchanged.combined] == [
        event.title for event in result.combined
    ]
