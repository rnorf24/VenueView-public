from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr

from .models import CalendarEvent


# VenueView intentionally does not ingest descriptions, contacts, URLs, or
# attachments in Core. Those fields may contain agreements or personal data.
ALLOWED_EVENT_PROPERTIES = frozenset(
    {
        "UID",
        "SUMMARY",
        "DTSTART",
        "DTEND",
        "DURATION",
        "RRULE",
        "RDATE",
        "EXDATE",
        "RECURRENCE-ID",
        "CATEGORIES",
        "LOCATION",
        "STATUS",
    }
)

BLOCKED_EVENT_PROPERTIES = frozenset(
    {
        "DESCRIPTION",
        "URL",
        "ATTACH",
        "ORGANIZER",
        "ATTENDEE",
        "CONTACT",
        "X-CALENDAR-WHO",
    }
)


@dataclass(frozen=True)
class ContentProperty:
    name: str
    params: dict[str, str]
    value: str


RawComponent = dict[str, list[ContentProperty]]


def unfold_lines(text: str) -> list[str]:
    """Unfold RFC 5545 continuation lines."""

    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    for line in raw_lines:
        if line.startswith((" ", "\t")) and output:
            output[-1] += line[1:]
        else:
            output.append(line)
    return output


def parse_content_line(line: str) -> ContentProperty:
    if ":" not in line:
        return ContentProperty(line.upper(), {}, "")
    left, value = line.split(":", 1)
    pieces = left.split(";")
    params: dict[str, str] = {}
    for item in pieces[1:]:
        if "=" in item:
            key, param_value = item.split("=", 1)
            params[key.upper()] = param_value.strip('"')
    return ContentProperty(pieces[0].upper(), params, value)


def read_event_components_from_text(text: str) -> list[RawComponent]:
    """Read whitelisted operational properties from VEVENT text."""

    lines = unfold_lines(text)
    events: list[RawComponent] = []
    current: defaultdict[str, list[ContentProperty]] | None = None
    for line in lines:
        marker = line.upper()
        if marker == "BEGIN:VEVENT":
            current = defaultdict(list)
            continue
        if marker == "END:VEVENT":
            if current is not None:
                events.append(dict(current))
            current = None
            continue
        if current is None:
            continue
        prop = parse_content_line(line)
        if prop.name in ALLOWED_EVENT_PROPERTIES:
            current[prop.name].append(prop)
    return events


def read_event_components(path: Path) -> list[RawComponent]:
    """Read only the whitelisted operational properties from a file."""

    return read_event_components_from_text(
        path.read_text(encoding="utf-8-sig", errors="replace")
    )


def _first(component: RawComponent, name: str) -> ContentProperty | None:
    values = component.get(name, [])
    return values[0] if values else None


def _unescape_text(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
        .strip()
    )


def _split_escaped_list(value: str) -> list[str]:
    pieces: list[str] = []
    buffer: list[str] = []
    escaped = False
    for character in value:
        if escaped:
            buffer.extend(("\\", character))
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ",":
            pieces.append(_unescape_text("".join(buffer)))
            buffer = []
        else:
            buffer.append(character)
    if escaped:
        buffer.append("\\")
    pieces.append(_unescape_text("".join(buffer)))
    return [piece for piece in pieces if piece]


def parse_categories(component: RawComponent) -> tuple[str, ...]:
    paths: list[str] = []
    for prop in component.get("CATEGORIES", []):
        for path in _split_escaped_list(prop.value):
            normalized = " > ".join(
                part.strip() for part in path.split(">") if part.strip()
            )
            if normalized and normalized not in paths:
                paths.append(normalized)
    return tuple(paths)


def _parse_datetime(
    prop: ContentProperty, default_tz: ZoneInfo
) -> tuple[datetime, bool]:
    raw = prop.value.strip()
    is_date = prop.params.get("VALUE", "").upper() == "DATE" or bool(
        re.fullmatch(r"\d{8}", raw)
    )
    if is_date:
        parsed_date = datetime.strptime(raw[:8], "%Y%m%d").date()
        return datetime.combine(parsed_date, time.min, tzinfo=default_tz), True

    if raw.endswith("Z"):
        parsed = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return parsed.astimezone(default_tz), False

    parsed: datetime | None = None
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            parsed = datetime.strptime(raw, fmt)
            break
        except ValueError:
            pass
    if parsed is None:
        raise ValueError(f"Unsupported iCalendar date/time: {raw!r}")

    timezone_name = prop.params.get("TZID", "")
    try:
        source_tz = ZoneInfo(timezone_name) if timezone_name else default_tz
    except Exception:
        source_tz = default_tz
    return parsed.replace(tzinfo=source_tz).astimezone(default_tz), False


def _parse_duration(value: str) -> timedelta:
    match = re.fullmatch(
        r"(?P<sign>[+-])?P(?:(?P<weeks>\d+)W)?(?:(?P<days>\d+)D)?"
        r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
        value.strip(),
    )
    if not match:
        raise ValueError(f"Unsupported iCalendar duration: {value!r}")
    duration = timedelta(
        weeks=int(match.group("weeks") or 0),
        days=int(match.group("days") or 0),
        hours=int(match.group("hours") or 0),
        minutes=int(match.group("minutes") or 0),
        seconds=int(match.group("seconds") or 0),
    )
    return -duration if match.group("sign") == "-" else duration


def _parse_datetime_list(
    properties: Iterable[ContentProperty], default_tz: ZoneInfo
) -> list[datetime]:
    output: list[datetime] = []
    for prop in properties:
        for raw_value in _split_escaped_list(prop.value):
            output.append(
                _parse_datetime(
                    ContentProperty(prop.name, prop.params, raw_value), default_tz
                )[0]
            )
    return output


def _component_identity(component: RawComponent) -> str:
    prop = _first(component, "UID")
    return _unescape_text(prop.value) if prop else ""


def _status(component: RawComponent) -> str:
    prop = _first(component, "STATUS")
    return prop.value.strip().upper() if prop else "CONFIRMED"


def _datetime_key(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _component_times(
    component: RawComponent,
    default_tz: ZoneInfo,
    fallback_start: datetime | None = None,
    fallback_end: datetime | None = None,
) -> tuple[datetime, datetime, bool]:
    start_prop = _first(component, "DTSTART")
    if start_prop:
        start, all_day = _parse_datetime(start_prop, default_tz)
    elif fallback_start is not None:
        start, all_day = fallback_start, False
    else:
        raise ValueError("VEVENT has no DTSTART")

    end_prop = _first(component, "DTEND")
    duration_prop = _first(component, "DURATION")
    if end_prop:
        end = _parse_datetime(end_prop, default_tz)[0]
    elif duration_prop:
        end = start + _parse_duration(duration_prop.value)
    elif fallback_start is not None and fallback_end is not None:
        end = start + (fallback_end - fallback_start)
    else:
        end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
    return start, end, all_day


def _event_instance(
    component: RawComponent,
    start: datetime,
    end: datetime,
    all_day: bool,
    recurring: bool,
    fallback_component: RawComponent | None = None,
) -> CalendarEvent:
    title_prop = _first(component, "SUMMARY") or (
        _first(fallback_component, "SUMMARY") if fallback_component else None
    )
    location_prop = _first(component, "LOCATION") or (
        _first(fallback_component, "LOCATION") if fallback_component else None
    )
    categories = parse_categories(component) or (
        parse_categories(fallback_component) if fallback_component else ()
    )
    uid = _component_identity(component) or (
        _component_identity(fallback_component) if fallback_component else ""
    )
    return CalendarEvent(
        source_uid=uid,
        title=_unescape_text(title_prop.value) if title_prop else "",
        start=start,
        end=end,
        categories=categories,
        source_location=_unescape_text(location_prop.value) if location_prop else "",
        all_day=all_day,
        recurring=recurring,
        status=_status(component),
    )


def _inside_window(
    event: CalendarEvent, window_start: datetime, window_end: datetime
) -> bool:
    return event.end > window_start and event.start < window_end


def _parse_components(
    components: list[RawComponent],
    *,
    window_start: datetime,
    window_end: datetime,
    default_timezone: str = "America/New_York",
) -> list[CalendarEvent]:
    """Expand an iCalendar file into occurrences inside ``[start, end)``.

    Callers must provide a bounded window. This prevents unbounded recurrence
    rules from generating an uncontrolled number of rows.
    """

    if window_end <= window_start:
        raise ValueError("window_end must be later than window_start")
    default_tz = ZoneInfo(default_timezone)
    if window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=default_tz)
    else:
        window_start = window_start.astimezone(default_tz)
    if window_end.tzinfo is None:
        window_end = window_end.replace(tzinfo=default_tz)
    else:
        window_end = window_end.astimezone(default_tz)

    masters: list[RawComponent] = []
    override_groups: defaultdict[str, list[RawComponent]] = defaultdict(list)
    for component in components:
        if _first(component, "RECURRENCE-ID"):
            override_groups[_component_identity(component)].append(component)
        else:
            masters.append(component)

    output: list[CalendarEvent] = []
    consumed_overrides: set[int] = set()
    for master in masters:
        if _status(master) == "CANCELLED":
            continue
        try:
            master_start, master_end, all_day = _component_times(master, default_tz)
        except ValueError:
            continue
        duration = master_end - master_start
        uid = _component_identity(master)

        overrides: dict[str, tuple[int, RawComponent]] = {}
        for override in override_groups.get(uid, []):
            recurrence_prop = _first(override, "RECURRENCE-ID")
            if not recurrence_prop:
                continue
            recurrence_start = _parse_datetime(recurrence_prop, default_tz)[0]
            overrides[_datetime_key(recurrence_start)] = (id(override), override)

        recurrence_prop = _first(master, "RRULE")
        starts: set[datetime] = {master_start}
        if recurrence_prop:
            rule = rrulestr(recurrence_prop.value.strip(), dtstart=master_start)
            starts = set(rule.between(window_start - duration, window_end, inc=True))
        starts.update(_parse_datetime_list(master.get("RDATE", []), default_tz))
        exclusions = {
            _datetime_key(value)
            for value in _parse_datetime_list(master.get("EXDATE", []), default_tz)
        }

        for occurrence_start in sorted(starts):
            key = _datetime_key(occurrence_start)
            if key in exclusions:
                continue
            override_item = overrides.get(key)
            if override_item:
                override_id, override = override_item
                consumed_overrides.add(override_id)
                if _status(override) == "CANCELLED":
                    continue
                override_start, override_end, override_all_day = _component_times(
                    override,
                    default_tz,
                    fallback_start=occurrence_start,
                    fallback_end=occurrence_start + duration,
                )
                event = _event_instance(
                    override,
                    override_start,
                    override_end,
                    override_all_day,
                    recurring=True,
                    fallback_component=master,
                )
            else:
                event = _event_instance(
                    master,
                    occurrence_start,
                    occurrence_start + duration,
                    all_day,
                    recurring=bool(recurrence_prop),
                )
            if _inside_window(event, window_start, window_end):
                output.append(event)

    # Preserve detached overrides even when a source omits their master event.
    for overrides in override_groups.values():
        for override in overrides:
            if id(override) in consumed_overrides or _status(override) == "CANCELLED":
                continue
            try:
                start, end, all_day = _component_times(override, default_tz)
            except ValueError:
                continue
            event = _event_instance(override, start, end, all_day, recurring=True)
            if _inside_window(event, window_start, window_end):
                output.append(event)

    return sorted(
        output,
        key=lambda event: (
            event.start,
            event.end,
            event.title.casefold(),
            event.source_uid,
        ),
    )


def parse_ics_text(
    text: str,
    *,
    window_start: datetime,
    window_end: datetime,
    default_timezone: str = "America/New_York",
) -> list[CalendarEvent]:
    """Parse an iCalendar payload without writing it to disk."""

    return _parse_components(
        read_event_components_from_text(text),
        window_start=window_start,
        window_end=window_end,
        default_timezone=default_timezone,
    )


def parse_ics(
    path: str | Path,
    *,
    window_start: datetime,
    window_end: datetime,
    default_timezone: str = "America/New_York",
) -> list[CalendarEvent]:
    """Expand an iCalendar file without retaining its raw text."""

    return _parse_components(
        read_event_components(Path(path)),
        window_start=window_start,
        window_end=window_end,
        default_timezone=default_timezone,
    )
