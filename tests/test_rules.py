import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from venueview.models import OperationalEvent
from venueview.rules import (
    RulePackValidationError,
    classify_event,
    load_rule_pack_text,
    merge_rule_packs,
)


def _pack(*, rule_id: str, priority: int, group: str):
    return load_rule_pack_text(
        json.dumps(
            {
                "schema_version": 1,
                "classification_rules": [
                    {
                        "id": rule_id,
                        "priority": priority,
                        "field": "title",
                        "operator": "contains",
                        "value": "SYNTHETIC MATCH KEY",
                        "assign": {"group": group},
                    }
                ],
                "ignore_rules": [],
                "combination_rules": [],
            }
        )
    )


def test_private_overlay_precedes_public_rules_regardless_of_numeric_priority():
    public = _pack(rule_id="public_rule", priority=1, group="Public Group")
    private = _pack(rule_id="private_rule", priority=999, group="Private Group")
    merged = merge_rule_packs(public, private)
    timezone = ZoneInfo("America/New_York")
    event = OperationalEvent(
        source_uid="synthetic-uid",
        title="SYNTHETIC MATCH KEY",
        start=datetime(2026, 7, 21, 9, tzinfo=timezone),
        end=datetime(2026, 7, 21, 10, tzinfo=timezone),
        category_path="Synthetic Venue > Synthetic Room",
        venue="Synthetic Venue",
        space="Synthetic Room",
    )

    classified = classify_event(event, merged)

    assert classified.group == "Private Group"
    assert classified.applied_rules == ["private_rule", "public_rule"]


def test_private_overlay_can_replace_public_rule_by_id():
    public = _pack(rule_id="shared_rule", priority=1, group="Public Group")
    private = _pack(rule_id="shared_rule", priority=999, group="Private Group")

    merged = merge_rule_packs(public, private)

    assert [rule.rule_id for rule in merged.classification_rules] == ["shared_rule"]
    assert merged.classification_rules[0].assign["group"] == "Private Group"


@pytest.mark.parametrize(
    "mutation, expected_message",
    [
        ({"schema_version": 99}, "schema_version"),
        (
            {
                "schema_version": 1,
                "classification_rules": [
                    {
                        "id": "bad_field",
                        "field": "description",
                        "value": "synthetic",
                        "assign": {"group": "Synthetic"},
                    }
                ],
            },
            "unsupported field",
        ),
    ],
)
def test_invalid_rule_pack_schema_is_rejected(mutation, expected_message):
    with pytest.raises(RulePackValidationError, match=expected_message):
        load_rule_pack_text(json.dumps(mutation))
