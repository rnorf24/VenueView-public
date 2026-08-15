from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from .audit import operational_event_dict, safe_audit_report
from .ics import parse_ics
from .pipeline import run_pipeline
from .profiles import load_profile
from .rules import load_rule_pack, merge_rule_packs


def _date_boundary(value: str, *, timezone_name: str = "America/New_York") -> datetime:
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    # End dates are exclusive; the UI can display this as "through previous day."
    return datetime.combine(parsed, time.min, tzinfo=ZoneInfo(timezone_name))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="venueview", description="VenueView calendar processing core"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("audit", "process"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("calendar", type=Path)
        subparser.add_argument(
            "--window-start", required=True, help="Inclusive date: YYYY-MM-DD"
        )
        subparser.add_argument(
            "--window-end", required=True, help="Exclusive date: YYYY-MM-DD"
        )
        subparser.add_argument("--timezone", default="America/New_York")
        subparser.add_argument("--profile", type=Path)
        subparser.add_argument("--rules", type=Path)
        subparser.add_argument(
            "--private-rules",
            type=Path,
            help="Optional private overlay applied before the public rule pack.",
        )
        subparser.add_argument("--output", type=Path)

    process = subparsers.choices["process"]
    process.add_argument("--mode", choices=("detailed", "combined"), default="combined")
    process.add_argument(
        "--allow-sensitive-output",
        action="store_true",
        help="Required because event titles can contain private operational data.",
    )
    return parser


def _load(args: argparse.Namespace):
    start = _date_boundary(args.window_start, timezone_name=args.timezone)
    end = _date_boundary(args.window_end, timezone_name=args.timezone)
    events = parse_ics(
        args.calendar,
        window_start=start,
        window_end=end,
        default_timezone=args.timezone,
    )
    profile = load_profile(args.profile) if args.profile else None
    rule_pack = load_rule_pack(args.rules) if args.rules else None
    if rule_pack and args.private_rules:
        rule_pack = merge_rule_packs(rule_pack, load_rule_pack(args.private_rules))
    result = run_pipeline(events, profile, rule_pack) if profile and rule_pack else None
    return events, profile, result


def _emit(payload: object, output: Path | None) -> None:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    events, profile, result = _load(args)
    if args.command == "audit":
        _emit(
            safe_audit_report(
                path=args.calendar,
                events=events,
                profile=profile,
                pipeline_result=result,
            ),
            args.output,
        )
        return 0

    if not args.allow_sensitive_output:
        raise SystemExit(
            "Refusing operational output: pass --allow-sensitive-output only for approved local processing. "
            "Use 'venueview audit' for a privacy-safe report."
        )
    if result is None:
        raise SystemExit("process requires both --profile and --rules")
    selected = result.combined if args.mode == "combined" else result.detailed
    _emit([operational_event_dict(event) for event in selected], args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
