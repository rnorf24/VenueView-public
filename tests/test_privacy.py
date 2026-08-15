import json
from datetime import datetime
from zoneinfo import ZoneInfo

from venueview.audit import safe_audit_report, scan_text_for_sensitive_patterns
from venueview.ics import parse_ics


def test_safe_audit_never_contains_titles_or_uids(project_root):
    calendar = project_root / "data/synthetic/sample_calendar.ics"
    timezone = ZoneInfo("America/New_York")
    events = parse_ics(
        calendar,
        window_start=datetime(2026, 7, 17, tzinfo=timezone),
        window_end=datetime(2026, 7, 20, tzinfo=timezone),
    )
    serialized = json.dumps(safe_audit_report(path=calendar, events=events))

    assert "Summit Skills - Open" not in serialized
    assert "synthetic-fs-open" not in serialized


def test_public_configuration_has_no_contact_or_agreement_patterns(project_root):
    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((project_root / "config").rglob("*.json"))
    )
    assert scan_text_for_sensitive_patterns(public_text) == []


def test_real_calendar_and_outputs_are_ignored(project_root):
    gitignore = (project_root / ".gitignore").read_text(encoding="utf-8")
    assert "*.ics" in gitignore
    assert "data/private/" in gitignore
    assert "config/private/" in gitignore
    assert "output/*" in gitignore


def test_private_reference_workbook_is_not_copied_into_public_project(project_root):
    assert list(project_root.rglob("*.xlsx")) == []
