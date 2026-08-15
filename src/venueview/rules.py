from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import OperationalEvent


@dataclass(frozen=True)
class MatchCondition:
    field: str
    operator: str
    value: str


@dataclass(frozen=True)
class ClassificationRule:
    rule_id: str
    priority: int
    conditions: tuple[MatchCondition, ...]
    assign: dict[str, str]


@dataclass(frozen=True)
class IgnoreRule:
    rule_id: str
    priority: int
    conditions: tuple[MatchCondition, ...]
    reason: str


@dataclass(frozen=True)
class CombinationRule:
    rule_id: str
    priority: int
    conditions: tuple[MatchCondition, ...]
    partition_by: tuple[str, ...]
    max_gap_minutes: int
    result: dict[str, str]
    enabled: bool = True


@dataclass(frozen=True)
class RulePack:
    classification_rules: tuple[ClassificationRule, ...] = ()
    ignore_rules: tuple[IgnoreRule, ...] = ()
    combination_rules: tuple[CombinationRule, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class RulePackValidationError(ValueError):
    """Raised when a rule pack is structurally unsafe or unsupported."""


SCHEMA_VERSION = 1
MAX_RULES_PER_PACK = 10_000
ALLOWED_FIELDS = {
    "all_day",
    "categories",
    "category_path",
    "function",
    "group",
    "local_date",
    "recurring",
    "source_uid",
    "space",
    "title",
    "venue",
}
ALLOWED_OPERATORS = {
    "contains",
    "ends",
    "ends_with",
    "endswith",
    "equals",
    "exact",
    "regex",
    "starts",
    "starts_with",
    "startswith",
}
ALLOWED_ASSIGN_FIELDS = {"group", "function"}
ALLOWED_RESULT_FIELDS = {"title", "group", "function"}


def _rule_location(section: str, index: int) -> str:
    return f"{section} rule {index + 1}"


def _require_mapping(value: Any, *, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RulePackValidationError(f"{location} must be a JSON object.")
    return value


def _require_rule_list(data: dict[str, Any], section: str) -> list[Any]:
    value = data.get(section, [])
    if not isinstance(value, list):
        raise RulePackValidationError(f"{section} must be a JSON array.")
    return value


def _validate_integer(
    value: Any,
    *,
    location: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RulePackValidationError(f"{location} must be an integer.")
    if minimum is not None and value < minimum:
        raise RulePackValidationError(f"{location} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise RulePackValidationError(f"{location} must be at most {maximum}.")


def _validate_conditions(rule: dict[str, Any], *, location: str) -> None:
    if "match_all" in rule:
        raw_conditions = rule["match_all"]
        if not isinstance(raw_conditions, list) or not raw_conditions:
            raise RulePackValidationError(
                f"{location} match_all must be a non-empty JSON array."
            )
    elif "field" in rule:
        raw_conditions = [rule]
    else:
        raise RulePackValidationError(
            f"{location} must define field/value or a non-empty match_all array."
        )

    for condition_index, raw_condition in enumerate(raw_conditions):
        condition_location = f"{location} condition {condition_index + 1}"
        condition = _require_mapping(raw_condition, location=condition_location)
        field_name = condition.get("field")
        if not isinstance(field_name, str) or field_name not in ALLOWED_FIELDS:
            raise RulePackValidationError(
                f"{condition_location} uses an unsupported field."
            )
        operator = condition.get("operator", "contains")
        if not isinstance(operator, str):
            raise RulePackValidationError(
                f"{condition_location} operator must be text."
            )
        normalized_operator = operator.casefold().replace("-", "_").replace(" ", "_")
        if normalized_operator not in ALLOWED_OPERATORS:
            raise RulePackValidationError(
                f"{condition_location} uses an unsupported operator."
            )
        value = condition.get("value")
        if not isinstance(value, str) or not value.strip():
            raise RulePackValidationError(
                f"{condition_location} value must be non-empty text."
            )
        if normalized_operator == "regex":
            try:
                re.compile(value, flags=re.IGNORECASE)
            except re.error as exc:
                raise RulePackValidationError(
                    f"{condition_location} contains an invalid regular expression."
                ) from exc


def _validate_assignment(
    value: Any,
    *,
    location: str,
    allowed_fields: set[str],
    required: bool,
) -> None:
    assignment = _require_mapping(value, location=location)
    if required and not assignment:
        raise RulePackValidationError(f"{location} cannot be empty.")
    unsupported = set(assignment) - allowed_fields
    if unsupported:
        raise RulePackValidationError(f"{location} contains an unsupported field.")
    for assigned_value in assignment.values():
        if not isinstance(assigned_value, str) or not assigned_value.strip():
            raise RulePackValidationError(
                f"{location} values must be non-empty text."
            )


def validate_rule_pack_data(data: Any) -> dict[str, Any]:
    """Validate rule-pack JSON without exposing its operational values."""

    pack = _require_mapping(data, location="Rule pack")
    if pack.get("schema_version") != SCHEMA_VERSION:
        raise RulePackValidationError(
            f"Rule pack schema_version must be {SCHEMA_VERSION}."
        )
    metadata = pack.get("metadata", {})
    _require_mapping(metadata, location="Rule pack metadata")

    sections = {
        "classification_rules": _require_rule_list(pack, "classification_rules"),
        "ignore_rules": _require_rule_list(pack, "ignore_rules"),
        "combination_rules": _require_rule_list(pack, "combination_rules"),
    }
    if sum(len(rules) for rules in sections.values()) > MAX_RULES_PER_PACK:
        raise RulePackValidationError(
            f"Rule pack cannot contain more than {MAX_RULES_PER_PACK} rules."
        )

    seen_ids: set[str] = set()
    for section, rules in sections.items():
        for index, raw_rule in enumerate(rules):
            location = _rule_location(section, index)
            rule = _require_mapping(raw_rule, location=location)
            rule_id = rule.get("id")
            if not isinstance(rule_id, str) or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", rule_id
            ) is None:
                raise RulePackValidationError(
                    f"{location} id must use 1-128 letters, numbers, dots, dashes, or underscores."
                )
            if rule_id in seen_ids:
                raise RulePackValidationError(f"{location} id must be unique.")
            seen_ids.add(rule_id)
            enabled = rule.get("enabled", True)
            if not isinstance(enabled, bool):
                raise RulePackValidationError(f"{location} enabled must be true or false.")
            _validate_integer(
                rule.get("priority", 100),
                location=f"{location} priority",
                minimum=-100_000,
                maximum=100_000,
            )
            _validate_conditions(rule, location=location)

            if section == "classification_rules":
                _validate_assignment(
                    rule.get("assign", {}),
                    location=f"{location} assign",
                    allowed_fields=ALLOWED_ASSIGN_FIELDS,
                    required=True,
                )
            elif section == "ignore_rules":
                reason = rule.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise RulePackValidationError(
                        f"{location} reason must be non-empty text."
                    )
            else:
                partition_by = rule.get(
                    "partition_by", ["local_date", "venue", "space", "group"]
                )
                if not isinstance(partition_by, list) or not partition_by:
                    raise RulePackValidationError(
                        f"{location} partition_by must be a non-empty JSON array."
                    )
                if any(
                    not isinstance(field_name, str)
                    or field_name not in ALLOWED_FIELDS
                    for field_name in partition_by
                ):
                    raise RulePackValidationError(
                        f"{location} partition_by contains an unsupported field."
                    )
                _validate_integer(
                    rule.get("max_gap_minutes", 15),
                    location=f"{location} max_gap_minutes",
                    minimum=0,
                    maximum=1_440,
                )
                _validate_assignment(
                    rule.get("result", {}),
                    location=f"{location} result",
                    allowed_fields=ALLOWED_RESULT_FIELDS,
                    required=False,
                )
    return pack


def _conditions(data: dict[str, Any]) -> tuple[MatchCondition, ...]:
    raw_conditions = data.get("match_all")
    if raw_conditions is None and "field" in data:
        raw_conditions = [
            {
                "field": data["field"],
                "operator": data.get("operator", "contains"),
                "value": data.get("value", ""),
            }
        ]
    return tuple(
        MatchCondition(
            field=str(condition["field"]),
            operator=str(condition.get("operator", "contains")),
            value=str(condition.get("value", "")),
        )
        for condition in (raw_conditions or [])
    )


def load_rule_pack_data(data: Any) -> RulePack:
    data = validate_rule_pack_data(data)
    classifications = tuple(
        sorted(
            (
                ClassificationRule(
                    rule_id=str(rule["id"]),
                    priority=int(rule.get("priority", 100)),
                    conditions=_conditions(rule),
                    assign={
                        str(key): str(value)
                        for key, value in rule.get("assign", {}).items()
                    },
                )
                for rule in data.get("classification_rules", [])
                if rule.get("enabled", True)
            ),
            key=lambda rule: rule.priority,
        )
    )
    ignores = tuple(
        sorted(
            (
                IgnoreRule(
                    rule_id=str(rule["id"]),
                    priority=int(rule.get("priority", 100)),
                    conditions=_conditions(rule),
                    reason=str(rule.get("reason", "Excluded by rule")),
                )
                for rule in data.get("ignore_rules", [])
                if rule.get("enabled", True)
            ),
            key=lambda rule: rule.priority,
        )
    )
    combinations = tuple(
        sorted(
            (
                CombinationRule(
                    rule_id=str(rule["id"]),
                    priority=int(rule.get("priority", 100)),
                    conditions=_conditions(rule),
                    partition_by=tuple(
                        str(value)
                        for value in rule.get(
                            "partition_by", ["local_date", "venue", "space", "group"]
                        )
                    ),
                    max_gap_minutes=int(rule.get("max_gap_minutes", 15)),
                    result={
                        str(key): str(value)
                        for key, value in rule.get("result", {}).items()
                    },
                    enabled=bool(rule.get("enabled", True)),
                )
                for rule in data.get("combination_rules", [])
            ),
            key=lambda rule: rule.priority,
        )
    )
    return RulePack(
        classifications, ignores, combinations, dict(data.get("metadata", {}))
    )


def load_rule_pack_text(text: str) -> RulePack:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RulePackValidationError(
            f"Rule pack is not valid JSON (line {exc.lineno}, column {exc.colno})."
        ) from exc
    return load_rule_pack_data(data)


def load_rule_pack(path: str | Path) -> RulePack:
    return load_rule_pack_text(Path(path).read_text(encoding="utf-8-sig"))


def merge_rule_packs(base: RulePack, overlay: RulePack | None) -> RulePack:
    """Apply an optional private overlay before the public base rules.

    Overlay rules take precedence even when their numeric priority is higher.
    Reusing a public rule id replaces that rule within the corresponding
    section instead of running both copies.
    """

    if overlay is None:
        return base

    def merged_rules(base_rules: tuple[Any, ...], overlay_rules: tuple[Any, ...]):
        overlay_ids = {rule.rule_id for rule in overlay_rules}
        return overlay_rules + tuple(
            rule for rule in base_rules if rule.rule_id not in overlay_ids
        )

    return RulePack(
        classification_rules=merged_rules(
            base.classification_rules, overlay.classification_rules
        ),
        ignore_rules=merged_rules(base.ignore_rules, overlay.ignore_rules),
        combination_rules=merged_rules(
            base.combination_rules, overlay.combination_rules
        ),
        metadata={**base.metadata, **overlay.metadata, "private_overlay_loaded": True},
    )


def event_field(event: OperationalEvent, field_name: str) -> str:
    if field_name == "local_date":
        return event.local_date.isoformat()
    if field_name == "categories":
        return event.category_path
    value = getattr(event, field_name, "")
    return str(value)


def condition_matches(event: OperationalEvent, condition: MatchCondition) -> bool:
    actual = event_field(event, condition.field).strip()
    expected = condition.value.strip()
    operator = condition.operator.casefold().replace("-", "_").replace(" ", "_")
    actual_folded = actual.casefold()
    expected_folded = expected.casefold()
    if not expected:
        return False
    if operator in {"exact", "equals"}:
        return actual_folded == expected_folded
    if operator in {"starts", "starts_with", "startswith"}:
        return actual_folded.startswith(expected_folded)
    if operator in {"ends", "ends_with", "endswith"}:
        return actual_folded.endswith(expected_folded)
    if operator == "regex":
        try:
            return re.search(expected, actual, flags=re.IGNORECASE) is not None
        except re.error:
            return False
    return expected_folded in actual_folded


def rule_matches(
    event: OperationalEvent, conditions: tuple[MatchCondition, ...]
) -> bool:
    return bool(conditions) and all(
        condition_matches(event, condition) for condition in conditions
    )


def classify_event(event: OperationalEvent, rule_pack: RulePack) -> OperationalEvent:
    for rule in rule_pack.classification_rules:
        if not rule_matches(event, rule.conditions):
            continue
        if rule.assign.get("group") and not event.group:
            event.group = rule.assign["group"]
        if rule.assign.get("function") and not event.function:
            event.function = rule.assign["function"]
        event.applied_rules.append(rule.rule_id)
    if not event.group:
        event.needs_review.append("Missing group classification")
    if not event.function:
        event.needs_review.append("Missing function classification")
    return event


def ignore_reason(event: OperationalEvent, rule_pack: RulePack) -> str:
    for rule in rule_pack.ignore_rules:
        if rule_matches(event, rule.conditions):
            return rule.reason
    return ""
