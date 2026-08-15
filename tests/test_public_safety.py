import json
from pathlib import Path


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_public_profile_is_marked_as_demonstration(project_root):
    profiles = sorted((project_root / "config/profiles").glob("*.json"))

    assert profiles
    assert all(_json(path)["pilot_status"] == "demonstration" for path in profiles)


def test_public_taxonomy_and_rules_declare_fictional_status(project_root):
    taxonomy = _json(project_root / "config/venue_taxonomy.json")
    rules = _json(project_root / "config/rules/public_rules.json")

    assert "fictional" in taxonomy["source_policy"].casefold()
    assert "fictional" in rules["metadata"]["privacy"].casefold()


def test_only_the_named_synthetic_calendar_fixture_is_present(project_root):
    calendars = sorted(
        path.relative_to(project_root).as_posix()
        for suffix in ("*.ics", "*.ical")
        for path in project_root.rglob(suffix)
    )

    assert calendars == ["data/synthetic/sample_calendar.ics"]
    fixture = (project_root / calendars[0]).read_text(encoding="utf-8")
    assert "synthetic" in fixture.casefold()


def test_no_operational_output_or_recording_artifacts_are_tracked(project_root):
    prohibited = {
        ".csv",
        ".doc",
        ".docx",
        ".mov",
        ".mp4",
        ".pdf",
        ".webm",
        ".xls",
        ".xlsx",
    }

    unexpected = [
        path.relative_to(project_root).as_posix()
        for path in project_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in prohibited
    ]
    assert unexpected == []
