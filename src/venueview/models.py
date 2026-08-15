from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class CalendarEvent:
    """One expanded occurrence from an iCalendar source.

    ``title`` and ``source_uid`` can contain internal information. They stay in
    memory during normal analysis and are deliberately omitted from safe audit
    reports.
    """

    source_uid: str
    title: str
    start: datetime
    end: datetime
    categories: tuple[str, ...] = ()
    source_location: str = ""
    all_day: bool = False
    recurring: bool = False
    status: str = "CONFIRMED"

    @property
    def local_date(self) -> date:
        return self.start.date()


@dataclass
class OperationalEvent:
    """Calendar occurrence after profile selection and classification."""

    source_uid: str
    title: str
    start: datetime
    end: datetime
    category_path: str
    venue: str
    space: str
    group: str = ""
    function: str = ""
    all_day: bool = False
    recurring: bool = False
    needs_review: list[str] = field(default_factory=list)
    source_count: int = 1
    applied_rules: list[str] = field(default_factory=list)
    locations: tuple[tuple[str, str], ...] = ()
    source_row_keys: tuple[str, ...] = ()

    @property
    def local_date(self) -> date:
        return self.start.date()

    def clone(self, **changes: Any) -> "OperationalEvent":
        return replace(self, **changes)


@dataclass(frozen=True)
class VenueProfile:
    profile_id: str
    name: str
    category_prefixes: tuple[str, ...]
    excluded_category_prefixes: tuple[str, ...] = ()
    allowed_spaces: tuple[str, ...] = ()
    output_modes: tuple[str, ...] = ("detailed", "combined", "both")
    pilot_status: str = "discovered"

    def includes_category(self, category_path: str) -> bool:
        normalized = category_path.casefold().strip()
        if any(
            normalized.startswith(prefix.casefold().strip())
            for prefix in self.excluded_category_prefixes
        ):
            return False
        if not any(
            normalized.startswith(prefix.casefold().strip())
            for prefix in self.category_prefixes
        ):
            return False
        if not self.allowed_spaces:
            return True
        leaf = category_path.rsplit(">", 1)[-1].strip().casefold()
        return leaf in {space.casefold() for space in self.allowed_spaces}
