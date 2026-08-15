from __future__ import annotations

import argparse
import hmac
import secrets
import sys
import time as clock
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from threading import Lock, Timer
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    Request,
    Response,
    jsonify,
    render_template_string,
    request,
    send_file,
    session,
)

from . import __version__
from .audit import operational_event_dict
from .exporters import build_csv_download, build_excel_download
from .ics import parse_ics_text
from .operational_rules import (
    MAX_PRIVATE_RULE_PACK_BYTES,
    bundled_private_rules_path,
    default_private_rules_path,
    load_optional_private_rule_pack,
    persist_private_rule_pack,
    remove_private_rule_pack,
)
from .pipeline import PipelineResult, run_pipeline
from .profiles import load_profile
from .review import (
    CombinationReview,
    apply_separation_overrides,
    combination_reviews,
)
from .rules import (
    RulePack,
    RulePackValidationError,
    load_rule_pack,
    load_rule_pack_text,
    merge_rule_packs,
)


PAGE = """
<!doctype html>
<html lang="en" data-csrf-token="{{ csrf_token }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VenueView</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; font-size: 100%; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f4f7fb; color: #182230; line-height: 1.5; }
    main { max-width: 980px; margin: 0 auto; padding: 36px 20px 64px; }
    header { margin-bottom: 24px; }
    h1 { margin: 0 0 6px; font-size: 2rem; }
    h2 { margin-top: 0; }
    .muted { color: #526274; }
    .version { display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: 999px; background: #e8eef6; color: #34465b; font-size: .78rem; vertical-align: middle; }
    .skip-link { position: absolute; left: 12px; top: -80px; padding: 10px 14px; background: white; color: #124a80; border: 2px solid #124a80; border-radius: 8px; z-index: 10; }
    .skip-link:focus { top: 12px; }
    .workflow { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 18px 0 6px; padding: 0; list-style: none; }
    .workflow li { background: #fff; border: 1px solid #d4deea; border-radius: 12px; padding: 14px; }
    .workflow strong { display: block; color: #123f69; }
    .step-number { display: inline-grid; place-items: center; width: 1.7rem; height: 1.7rem; margin-right: 7px; border-radius: 50%; background: #1259a6; color: white; font-size: .85rem; }
    .notice { padding: 12px 14px; border-radius: 10px; background: #e8f2ff; border: 1px solid #bbd8f7; }
    .loaded { padding: 12px 14px; border-radius: 10px; background: #eef9f1; border: 1px solid #b8dfc0; color: #205d2b; }
    .status-idle { padding: 12px 14px; border-radius: 10px; background: #f7f9fc; border: 1px solid #dce4ee; color: #3f5064; }
    .status-error { padding: 12px 14px; border-radius: 10px; background: #fff7df; border: 1px solid #efd58c; color: #6b4300; }
    .card { background: white; border: 1px solid #dce4ee; border-radius: 14px; padding: 22px; margin-top: 18px; box-shadow: 0 3px 12px rgba(30, 50, 80, .05); }
    .download-help { border: 1px solid #cbd7e6; border-radius: 10px; background: #f7f9fc; padding: 0; }
    .download-help summary { cursor: pointer; color: #124a80; font-weight: 700; padding: 12px 14px; }
    .download-help[open] summary { border-bottom: 1px solid #dce4ee; }
    .download-help-content { padding: 2px 16px 14px; }
    .download-help-content ol { padding-left: 1.4rem; }
    .download-help-content li { margin: 7px 0; }
    .privacy-note { color: #6b4300; background: #fff7df; border: 1px solid #efd58c; padding: 10px 12px; border-radius: 8px; }
    form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    label { display: grid; gap: 7px; font-weight: 650; }
    input, select, button { font: inherit; }
    input[type=file], input[type=date], select { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #b8c5d5; border-radius: 8px; background: white; }
    .full { grid-column: 1 / -1; }
    .checkbox { display: flex; grid-template-columns: none; align-items: flex-start; gap: 9px; font-weight: 500; }
    .checkbox input { margin-top: 4px; }
    button, .button-link { min-height: 44px; border: 0; border-radius: 8px; background: #1259a6; color: white; padding: 11px 16px; cursor: pointer; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; }
    button:hover { background: #0d4786; }
    button.secondary, .button-link.secondary { background: #e8f2ff; color: #124a80; border: 1px solid #a9caed; }
    button.secondary:hover, .button-link.secondary:hover { background: #d8eafb; }
    button.quit { background: #fff5f3; color: #8b2c22; border: 1px solid #e7b8b1; }
    button.quit:hover { background: #ffe7e3; }
    .quit-form { display: flex; justify-content: flex-end; margin-top: 18px; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; }
    .error { color: #8d1f1f; background: #fff0f0; border: 1px solid #efb8b8; padding: 12px; border-radius: 9px; }
    .success { color: #205d2b; background: #eef9f1; border: 1px solid #b8dfc0; padding: 12px; border-radius: 9px; }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .metric { background: #f7f9fc; border-radius: 9px; padding: 12px; }
    .metric strong { display: block; font-size: 1.35rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; font-size: .9rem; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e5eaf0; vertical-align: top; }
    th { color: #4e5e71; }
    .warning { color: #7b4a00; background: #fff7df; border: 1px solid #efd58c; padding: 10px; border-radius: 8px; margin-top: 10px; }
    .review-card { border: 1px solid #cbd7e6; border-radius: 12px; padding: 16px; margin-top: 14px; background: #fbfcfe; }
    .review-card h4 { margin: 0 0 6px; font-size: 1.05rem; }
    .review-meta { margin: 0 0 10px; color: #536477; }
    .decision-form { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
    button.active { background: #24723b; }
    button[disabled] { cursor: default; opacity: .9; }
    .gap { color: #6b4c00; font-weight: 650; }
    .support-code { display: block; margin-top: 6px; font-weight: 700; letter-spacing: .03em; }
    :focus-visible { outline: 3px solid #f2a900; outline-offset: 3px; }
    @media (max-width: 680px) { form, .metrics, .workflow { grid-template-columns: 1fr; } .full { grid-column: auto; } main { padding: 24px 14px 48px; } }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; } }
  </style>
</head>
<body data-restore-scroll="{{ restore_scroll }}">
<a class="skip-link" href="#main-content">Skip to main content</a>
<main id="main-content">
  <header>
    <h1>VenueView <span class="version">v{{ version }}</span></h1>
    <p class="muted">Local calendar processing for venue operations</p>
    <div class="notice">Calendar data and operational rules are processed on this computer. VenueView does not upload them.</div>
    <ol class="workflow" aria-label="VenueView workflow">
      <li><strong><span class="step-number">1</span>Check settings</strong><span>Confirm organization settings are ready.</span></li>
      <li><strong><span class="step-number">2</span>Choose calendar</strong><span>Select the venue and reporting dates.</span></li>
      <li><strong><span class="step-number">3</span>Review and export</strong><span>Preview results, review merges, then download.</span></li>
    </ol>
  </header>

  <section class="card">
    <h2>Step 1: Organization settings</h2>
    {% if message %}<div class="success" role="status">{{ message }}</div>{% endif %}
    {% if rules_status.state == 'loaded' %}
      <div class="loaded" data-rules-source="{{ rules_status.source }}" role="status"><strong>Organization settings are ready.</strong> {% if rules_status.source == 'bundled' %}Using the approved built-in settings.{% else %}Using imported replacement settings.{% endif %} {{ rules_status.classification_count }} classification, {{ rules_status.ignore_count }} exclusion, and {{ rules_status.combination_count }} combination rules are active.</div>
      {% if rules_status.detail %}<div class="status-error">{{ rules_status.detail }}</div>{% endif %}
    {% elif rules_status.state == 'error' %}
      <div class="status-error" role="alert"><strong>Organization settings need attention.</strong> {{ rules_status.detail }}</div>
    {% else %}
      <div class="status-idle" role="status"><strong>Standard public settings are active.</strong> No organization-specific settings are installed.</div>
    {% endif %}
    <p class="muted">An imported organization-settings file is checked and stored privately on this computer. It replaces the built-in settings until you restore the defaults.</p>
    <form method="post" action="/operational-rules/import" enctype="multipart/form-data">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <label class="full">Organization settings file (.json)
        <input type="file" name="rules_file" accept=".json,application/json" required>
      </label>
      <div class="full actions">
        <button class="secondary" type="submit">Import replacement settings</button>
      </div>
    </form>
    {% if rules_status.source == 'imported' %}
    <form method="post" action="/operational-rules/restore-defaults">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <div class="full actions">
        <button class="secondary" type="submit">Restore built-in settings</button>
      </div>
    </form>
    {% endif %}
  </section>

  <section class="card">
    <h2>Step 2: Choose calendar and dates</h2>
    {% if error %}<div class="error" role="alert">{{ error }}{% if error_code %}<span class="support-code">Support code: {{ error_code }}</span>{% endif %}</div>{% endif %}
    {% if calendar_loaded %}<div class="loaded">A calendar is loaded for this session. It is retained only in memory for up to 30 minutes after the last use; choose another file to replace it.</div>{% endif %}
    <form id="process-form" method="post" action="/process" enctype="multipart/form-data">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <label class="full">Calendar export (.ics)
        <input type="file" name="calendar" accept=".ics,.ical,text/calendar">
      </label>
      <details class="download-help full">
        <summary>How do I export an .ics calendar file?</summary>
        <div class="download-help-content">
          <ol>
            <li>Open the calendar system's export or sharing settings.</li>
            <li>Choose an <strong>iCalendar</strong> or <strong>ICS</strong> export.</li>
            <li>Select the calendars or categories needed for the report.</li>
            <li>Download the resulting <strong>.ics</strong> file, then choose it above.</li>
          </ol>
          <p class="muted">Export steps vary by calendar provider. Ask an authorized calendar administrator if the option is unavailable.</p>
          <p class="privacy-note"><strong>Keep it private:</strong> Do not share the feed link or downloaded calendar file outside the approved workflow.</p>
        </div>
      </details>
      <label>Venue profile
        <select name="profile" required>
          {% for profile in profiles %}
          <option value="{{ profile.profile_id }}"{% if form_state.profile_id == profile.profile_id %} selected{% endif %}>{{ profile.name }}{% if profile.pilot_status == 'pilot' %} (Pilot){% endif %}</option>
          {% endfor %}
        </select>
      </label>
      <label>Event view
        <select name="mode">
          <option value="combined"{% if form_state.mode == 'combined' %} selected{% endif %}>Combine Events</option>
          <option value="detailed"{% if form_state.mode == 'detailed' %} selected{% endif %}>Detailed Events</option>
          <option value="both"{% if form_state.mode == 'both' %} selected{% endif %}>Both Event Views</option>
        </select>
      </label>
      <label>First day to include
        <input type="date" name="window_start" value="{{ form_state.window_start }}" required>
      </label>
      <label>Last day to include
        <input type="date" name="window_end" value="{{ form_state.window_end }}" required>
      </label>
      <label class="checkbox full">
        <input type="checkbox" name="group_multi_location"{% if form_state.group_multi_location %} checked{% endif %}>
        <span>Group one source event assigned to multiple locations into a single multi-location event.</span>
      </label>
      <label class="checkbox full">
        <input type="checkbox" name="allow_sensitive_output"{% if form_state.allow_sensitive_output %} checked{% endif %}>
        <span>I understand that previews and downloads can contain private operational titles and group names.</span>
      </label>
      <p class="muted full">Your dates and selections stay loaded until you change them or quit VenueView.</p>
      <div class="full actions">
        <button type="submit" name="action" value="preview">Preview results</button>
        <button class="secondary" type="submit" name="action" value="csv">Download CSV</button>
        <button class="secondary" type="submit" name="action" value="excel">Download Excel</button>
        <button class="secondary" type="submit" name="action" value="clear">Clear loaded calendar</button>
      </div>
    </form>
  </section>

  {% if result %}
  <section class="card">
    <h2>Step 3: Review and export</h2>
    <h3>Processing summary</h3>
    <p class="muted">Profile: {{ result.profile_name }} · View: {{ result.mode }} · Multi-location grouping: {{ 'On' if result.group_multi_location else 'Off' }} · {{ result.window_start }} through {{ result.window_end }} (inclusive)</p>
    <div class="metrics">
      <div class="metric"><strong>{{ result.source_occurrences }}</strong><span>calendar occurrences</span></div>
      <div class="metric"><strong>{{ result.detailed_rows }}</strong><span>detailed events</span></div>
      <div class="metric"><strong>{{ result.combined_rows }}</strong><span>combined events</span></div>
      <div class="metric"><strong>{{ result.review_rows }}</strong><span>events needing review</span></div>
    </div>
    {% for warning in result.warnings %}<div class="warning">{{ warning }}</div>{% endfor %}
    {% if result.show_rows %}
      <h3>Local operational preview</h3>
      {% if result.truncated %}<p class="muted">Only the first 250 rows are shown in this prototype.</p>{% endif %}
      <table>
        <thead><tr><th>Date</th><th>Time</th><th>Venue</th><th>Space</th><th>Group</th><th>Function</th><th>Title</th></tr></thead>
        <tbody>
        {% for row in result.rows %}
          <tr><td>{{ row.date }}</td><td>{{ row.display_time }}</td><td>{{ row.venue }}</td><td>{{ row.space }}</td><td>{{ row.group }}</td><td>{{ row.function }}</td><td>{{ row.title }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
      {% if result.combination_reviews %}
      <h3>Combination review</h3>
      <p class="muted">These decisions apply to this in-memory calendar session and will be used by subsequent CSV and Excel exports.</p>
      {% for review in result.combination_reviews %}
      <article class="review-card">
        <h4>{{ review.title }}</h4>
        <p class="review-meta">{{ review.date }} · {{ review.display_time }} · {{ review.venue }} — {{ review.space }} · Rule: {{ review.rule_label }}</p>
        <table>
          <thead><tr><th>Source event</th><th>Time</th><th>Location</th><th>Gap</th></tr></thead>
          <tbody>
          {% for component in review.components %}
            <tr><td>{{ component.title }}</td><td>{{ component.display_time }}</td><td>{{ component.venue }} — {{ component.space }}</td><td class="gap">{{ component.gap_label }}</td></tr>
          {% endfor %}
          </tbody>
        </table>
        <form class="decision-form" method="post" action="/process">
          <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
          <input type="hidden" name="profile" value="{{ result.profile_id }}">
          <input type="hidden" name="mode" value="{{ result.mode_value }}">
          <input type="hidden" name="window_start" value="{{ result.window_start }}">
          <input type="hidden" name="window_end" value="{{ result.window_end }}">
          <input type="hidden" name="allow_sensitive_output" value="on">
          {% if result.group_multi_location %}<input type="hidden" name="group_multi_location" value="on">{% endif %}
          <input type="hidden" name="combination_id" value="{{ review.combination_id }}">
          <button type="submit" name="action" value="keep_combined"{% if review.decision == 'combined' %} class="active" disabled{% endif %}>Keep as one event</button>
          <button type="submit" name="action" value="separate_combination"{% if review.decision == 'separate' %} class="active" disabled{% else %} class="secondary"{% endif %}>Keep events separate</button>
        </form>
      </article>
      {% endfor %}
      {% endif %}
    {% else %}
      <p class="muted">Safe summary only. Check the acknowledgement box to preview event titles locally.</p>
    {% endif %}
  </section>
  {% endif %}

  <section class="card">
    <h2>Help and support</h2>
    <p class="muted">Download a privacy-safe support summary containing the VenueView version, settings status, and latest support code. It does not include calendar values, filenames, or file paths.</p>
    <a class="button-link secondary" href="/support-summary">Download support summary</a>
  </section>

  <form class="quit-form" method="post" action="/quit">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <button class="quit" type="submit">Quit VenueView</button>
  </form>
</main>
<script src="/runtime.js" defer></script>
</body>
</html>
"""


RUNTIME_JAVASCRIPT = r"""
(() => {
  "use strict";
  const csrfToken = document.documentElement.dataset.csrfToken;
  const pageId = globalThis.crypto && globalThis.crypto.randomUUID
    ? globalThis.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  const encodedState = () => new URLSearchParams({
    csrf_token: csrfToken,
    page_id: pageId,
  }).toString();

  const restoreScrollPosition = () => {
    const position = Number.parseInt(document.body.dataset.restoreScroll, 10);
    if (!Number.isFinite(position) || position < 0) return;
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
    requestAnimationFrame(() => {
      requestAnimationFrame(() => scrollTo(0, position));
    });
  };

  const rememberScrollPosition = (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    let field = form.querySelector('input[name="scroll_position"]');
    if (!field) {
      field = document.createElement("input");
      field.type = "hidden";
      field.name = "scroll_position";
      form.appendChild(field);
    }
    field.value = String(Math.max(0, Math.round(scrollY)));
  };

  const registerPage = () => {
    fetch("/runtime/browser-opened", {
      method: "POST",
      credentials: "same-origin",
      keepalive: true,
      headers: {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
      body: encodedState(),
    }).catch(() => {});
  };

  document.addEventListener("submit", rememberScrollPosition);
  restoreScrollPosition();
  registerPage();
  addEventListener("pageshow", registerPage);
  addEventListener("pagehide", () => {
    const payload = new Blob([encodedState()], {
      type: "application/x-www-form-urlencoded;charset=UTF-8",
    });
    navigator.sendBeacon("/runtime/browser-closed", payload);
  });
})();
"""


UPLOAD_TTL_SECONDS = 30 * 60
MAX_UPLOAD_SESSIONS = 8
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_SEPARATION_OVERRIDES = 500
BROWSER_CLOSE_GRACE_SECONDS = 2.0
SHUTDOWN_RESPONSE_GRACE_SECONDS = 0.2
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
PROCESS_FORM_STATE_SESSION_KEY = "process_form_state"
MAX_RESTORED_SCROLL_POSITION = 10_000_000


@dataclass
class _UploadState:
    text: str
    last_access: float
    separate_combinations: set[str] = field(default_factory=set)


class _MemoryRequest(Request):
    """Keep multipart file streams in memory instead of Werkzeug temp files.

    VenueView is deliberately a local, small-file workflow.  The explicit
    limit prevents this privacy choice from becoming an unbounded memory
    allocation.  The source bytes are still discarded when the process exits
    or the session is cleared/expired.
    """

    max_form_memory_size = MAX_UPLOAD_BYTES

    def _get_file_stream(self, *args: Any, **kwargs: Any):
        return BytesIO()


def _is_loopback_host(value: str | None) -> bool:
    if not value:
        return False
    try:
        host = urlsplit(f"//{value}").hostname
    except ValueError:
        return False
    return host in LOCAL_HOSTS


def _candidate_config_root() -> Path:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS")) / "config")
    candidates.extend(
        [
            Path.cwd() / "config",
            Path(__file__).resolve().parents[2] / "config",
        ]
    )
    for candidate in candidates:
        if (candidate / "profiles").is_dir() and (candidate / "rules").is_dir():
            return candidate
    return candidates[0]


def _load_profiles(config_root: Path) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    for path in sorted((config_root / "profiles").glob("*.json")):
        profile = load_profile(path)
        profiles[profile.profile_id] = profile
    return profiles


def _date_boundary(value: str, timezone_name: str) -> datetime:
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    return datetime.combine(parsed, time.min, tzinfo=ZoneInfo(timezone_name))


def _display_time(*, start: datetime, end: datetime, all_day: bool) -> str:
    if all_day:
        return "All Day"
    return f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def _review_payload(
    review: CombinationReview, *, decision: str
) -> dict[str, Any]:
    component_rows: list[dict[str, str]] = []
    previous_end: datetime | None = None
    for component in review.components:
        gap_label = "—"
        if previous_end is not None and not component.all_day:
            gap_minutes = round((component.start - previous_end).total_seconds() / 60)
            if gap_minutes > 0:
                gap_label = f"{gap_minutes} min gap"
            elif gap_minutes == 0:
                gap_label = "Touching"
            else:
                gap_label = f"{abs(gap_minutes)} min overlap"
        component_rows.append(
            {
                "title": component.title,
                "display_time": _display_time(
                    start=component.start,
                    end=component.end,
                    all_day=component.all_day,
                ),
                "venue": component.venue,
                "space": component.space,
                "gap_label": gap_label,
            }
        )
        previous_end = (
            max(previous_end, component.end) if previous_end else component.end
        )

    rule_label = ", ".join(
        rule_id.removeprefix("combine_").replace("_", " ").title()
        for rule_id in review.rule_ids
    ) or "Configured event combination"
    return {
        "combination_id": review.combination_id,
        "title": review.event.title,
        "date": review.event.local_date.isoformat(),
        "display_time": _display_time(
            start=review.event.start,
            end=review.event.end,
            all_day=review.event.all_day,
        ),
        "venue": review.event.venue,
        "space": review.event.space,
        "rule_label": rule_label,
        "decision": decision,
        "components": component_rows,
    }


def _result_payload(
    *,
    events: list[Any],
    pipeline_result: PipelineResult,
    profile_name: str,
    profile_id: str,
    mode: str,
    window_start: str,
    window_end: str,
    show_rows: bool,
    group_multi_location: bool,
    reviews: tuple[CombinationReview, ...] = (),
    separate_ids: set[str] | None = None,
) -> dict[str, Any]:
    selected = (
        pipeline_result.combined
        if mode in {"combined", "both"}
        else pipeline_result.detailed
    )
    rows: list[dict[str, Any]] = []
    if show_rows:
        for event in selected[:250]:
            row = operational_event_dict(event)
            row["display_time"] = _display_time(
                start=event.start,
                end=event.end,
                all_day=event.all_day,
            )
            rows.append(row)
    current_separate_ids = separate_ids or set()
    review_rows = (
        [
            _review_payload(
                review,
                decision=(
                    "separate"
                    if review.combination_id in current_separate_ids
                    else "combined"
                ),
            )
            for review in reviews
        ]
        if show_rows
        else []
    )
    warnings: list[str] = []
    if pipeline_result.unassigned_source_count:
        warnings.append(
            f"{pipeline_result.unassigned_source_count} source occurrences fell "
            "outside the selected profile."
        )
    if pipeline_result.excluded_count:
        warnings.append(
            f"{pipeline_result.excluded_count} rows were excluded by configured rules."
        )
    if sum(bool(event.needs_review) for event in pipeline_result.detailed):
        warnings.append(
            "Some events require human review before operational distribution."
        )
    return {
        "source_occurrences": len(events),
        "detailed_rows": len(pipeline_result.detailed),
        "combined_rows": len(pipeline_result.combined),
        "review_rows": sum(
            bool(event.needs_review) for event in pipeline_result.detailed
        ),
        "profile_name": profile_name,
        "profile_id": profile_id,
        "mode": {
            "combined": "Combine Events",
            "detailed": "Detailed Events",
            "both": "Both Event Views",
        }[mode],
        "mode_value": mode,
        "group_multi_location": group_multi_location,
        "window_start": window_start,
        "window_end": window_end,
        "warnings": warnings,
        "show_rows": show_rows,
        "rows": rows,
        "combination_reviews": review_rows,
        "truncated": show_rows and len(selected) > len(rows),
    }


def create_app(
    config_root: str | Path | None = None,
    private_rules_path: str | Path | None = None,
    bundled_rules_path: str | Path | None = None,
) -> Flask:
    root = Path(config_root) if config_root else _candidate_config_root()
    profiles = _load_profiles(root)
    rules_path = root / "rules" / "public_rules.json"
    public_rule_pack = load_rule_pack(rules_path)
    operational_rules_path = (
        Path(private_rules_path)
        if private_rules_path is not None
        else default_private_rules_path()
    )
    try:
        packaged_rules_path = (
            Path(bundled_rules_path)
            if bundled_rules_path is not None
            else bundled_private_rules_path(root)
        )
        packaged_rules_error = ""
    except (OSError, ValueError):
        packaged_rules_path = None
        packaged_rules_error = (
            "The built-in operational rule pack is unavailable. Import an "
            "approved replacement JSON file."
        )

    app = Flask(__name__)
    app.request_class = _MemoryRequest
    app.secret_key = secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
    # The service is intentionally HTTP on loopback. Setting Secure here
    # would prevent the browser from sending the cookie to 127.0.0.1.
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["VENUEVIEW_CONFIG_ROOT"] = str(root)
    app.config["VENUEVIEW_PRIVATE_RULES_PATH"] = str(operational_rules_path)
    app.config["VENUEVIEW_REQUEST_SHUTDOWN"] = None

    uploads: dict[str, _UploadState] = {}
    uploads_lock = Lock()
    rules_lock = Lock()
    private_rules: list[RulePack | None] = [None]
    private_rules_error: list[str] = [""]
    private_rules_source: list[str] = [""]
    active_pages: set[str] = set()
    pages_lock = Lock()
    pending_shutdown: list[Any | None] = [None]

    try:
        private_rules[0] = load_optional_private_rule_pack(operational_rules_path)
        if private_rules[0] is not None:
            private_rules_source[0] = "imported"
    except (OSError, UnicodeError, ValueError, RulePackValidationError):
        private_rules_error[0] = (
            "The saved replacement rule pack could not be validated. VenueView "
            "is using its built-in private rules; import a corrected file to "
            "replace them."
        )

    if private_rules[0] is None and packaged_rules_path is not None:
        try:
            private_rules[0] = load_optional_private_rule_pack(packaged_rules_path)
            if private_rules[0] is not None:
                private_rules_source[0] = "bundled"
        except (OSError, UnicodeError, ValueError, RulePackValidationError):
            packaged_rules_error = (
                "The built-in operational rule pack could not be validated. "
                "Import an approved replacement JSON file."
            )

    if private_rules[0] is None and packaged_rules_error:
        private_rules_error[0] = packaged_rules_error

    def _effective_rule_pack() -> RulePack:
        with rules_lock:
            return merge_rule_packs(public_rule_pack, private_rules[0])

    def _rules_status() -> dict[str, Any]:
        with rules_lock:
            active = private_rules[0]
            error = private_rules_error[0]
            source = private_rules_source[0]
        if active is not None:
            return {
                "state": "loaded",
                "source": source,
                "classification_count": len(active.classification_rules),
                "ignore_count": len(active.ignore_rules),
                "combination_count": len(
                    [rule for rule in active.combination_rules if rule.enabled]
                ),
                "detail": error,
            }
        if error:
            return {
                "state": "error",
                "source": "",
                "classification_count": 0,
                "ignore_count": 0,
                "combination_count": 0,
                "detail": error,
            }
        return {
            "state": "public_only",
            "source": "",
            "classification_count": 0,
            "ignore_count": 0,
            "combination_count": 0,
            "detail": "",
        }

    def _remove_expired_uploads(now: float | None = None) -> None:
        current = now if now is not None else clock.monotonic()
        with uploads_lock:
            expired = [
                token
                for token, state in uploads.items()
                if current - state.last_access > UPLOAD_TTL_SECONDS
            ]
            for token in expired:
                uploads.pop(token, None)

    def _get_upload_text() -> str | None:
        token = session.get("upload_token")
        if not token:
            return None
        now = clock.monotonic()
        _remove_expired_uploads(now)
        with uploads_lock:
            state = uploads.get(token)
            if state is None:
                session.pop("upload_token", None)
                return None
            state.last_access = now
            return state.text

    def _get_separation_overrides() -> set[str]:
        token = session.get("upload_token")
        if not token:
            return set()
        now = clock.monotonic()
        _remove_expired_uploads(now)
        with uploads_lock:
            state = uploads.get(token)
            if state is None:
                session.pop("upload_token", None)
                return set()
            state.last_access = now
            return set(state.separate_combinations)

    def _set_separation_override(review_id: str, *, separate: bool) -> None:
        token = session.get("upload_token")
        if not token:
            return
        with uploads_lock:
            state = uploads.get(token)
            if state is None:
                return
            if separate:
                if len(state.separate_combinations) < MAX_SEPARATION_OVERRIDES:
                    state.separate_combinations.add(review_id)
            else:
                state.separate_combinations.discard(review_id)
            state.last_access = clock.monotonic()

    def _remember_upload(text: str) -> None:
        now = clock.monotonic()
        token = session.get("upload_token") or secrets.token_urlsafe(32)
        _remove_expired_uploads(now)
        with uploads_lock:
            uploads[token] = _UploadState(text=text, last_access=now)
            while len(uploads) > MAX_UPLOAD_SESSIONS:
                oldest = min(uploads, key=lambda key: uploads[key].last_access)
                uploads.pop(oldest, None)
        session["upload_token"] = token

    def _clear_upload() -> None:
        token = session.pop("upload_token", None)
        if token:
            with uploads_lock:
                uploads.pop(token, None)

    def _is_valid_page_id(page_id: str) -> bool:
        return 8 <= len(page_id) <= 128 and all(
            character.isalnum() or character in {"-", "_"}
            for character in page_id
        )

    def _cancel_pending_shutdown_locked() -> None:
        timer = pending_shutdown[0]
        if timer is not None:
            timer.cancel()
            pending_shutdown[0] = None

    def _shutdown_if_no_pages() -> None:
        with pages_lock:
            pending_shutdown[0] = None
            if active_pages:
                return
        with uploads_lock:
            uploads.clear()
        callback = app.config.get("VENUEVIEW_REQUEST_SHUTDOWN")
        if callback is not None:
            callback()

    def _schedule_shutdown_if_no_pages(delay: float) -> None:
        with pages_lock:
            if active_pages:
                return
            _cancel_pending_shutdown_locked()
            timer = Timer(delay, _shutdown_if_no_pages)
            timer.daemon = True
            pending_shutdown[0] = timer
        timer.start()

    def _get_csrf_token() -> str:
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def _current_form_state() -> dict[str, Any]:
        stored = session.get(PROCESS_FORM_STATE_SESSION_KEY, {})
        if not isinstance(stored, dict):
            stored = {}
        default_profile_id = next(iter(profiles), "")
        profile_id = stored.get("profile_id", default_profile_id)
        if profile_id not in profiles:
            profile_id = default_profile_id
        mode = stored.get("mode", "combined")
        if mode not in {"detailed", "combined", "both"}:
            mode = "combined"

        def remembered_text(name: str) -> str:
            value = stored.get(name, "")
            return value if isinstance(value, str) and len(value) <= 32 else ""

        return {
            "profile_id": profile_id,
            "mode": mode,
            "window_start": remembered_text("window_start"),
            "window_end": remembered_text("window_end"),
            "group_multi_location": stored.get("group_multi_location") is True,
            "allow_sensitive_output": stored.get("allow_sensitive_output") is True,
        }

    def _remember_process_form_state(
        *,
        profile_id: str,
        mode: str,
        window_start: str,
        window_end: str,
        group_multi_location: bool,
        allow_sensitive_output: bool,
    ) -> None:
        session[PROCESS_FORM_STATE_SESSION_KEY] = {
            "profile_id": profile_id,
            "mode": mode,
            "window_start": window_start,
            "window_end": window_end,
            "group_multi_location": group_multi_location,
            "allow_sensitive_output": allow_sensitive_output,
        }

    def _requested_scroll_position() -> str:
        if request.method != "POST":
            return ""
        raw = request.form.get("scroll_position", "")
        if not raw.isascii() or not raw.isdecimal():
            return ""
        position = int(raw)
        if position > MAX_RESTORED_SCROLL_POSITION:
            return ""
        return str(position)

    def _has_valid_csrf_token() -> bool:
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "")
        return bool(
            expected
            and supplied
            and hmac.compare_digest(expected, supplied)
        )

    def _render(
        *,
        error: str = "",
        error_code: str = "",
        message: str = "",
        result: dict[str, Any] | None = None,
        status: int = 200,
    ):
        if error_code:
            session["last_error_code"] = error_code
        return (
            render_template_string(
                PAGE,
                profiles=list(profiles.values()),
                error=error,
                error_code=error_code,
                message=message,
                result=result,
                form_state=_current_form_state(),
                rules_status=_rules_status(),
                csrf_token=_get_csrf_token(),
                calendar_loaded=_get_upload_text() is not None,
                restore_scroll=_requested_scroll_position(),
                version=__version__,
            ),
            status,
        )

    def _is_local_host(value: str | None) -> bool:
        if not value:
            return False
        try:
            host = urlsplit(f"//{value}").hostname
        except ValueError:
            return False
        return host in LOCAL_HOSTS

    @app.before_request
    def enforce_local_request():
        # VenueView must never be exposed on a LAN or public interface. A
        # copied URL or proxy cannot turn it into a network service by accident.
        if not _is_local_host(request.host):
            return jsonify({"error": "VenueView accepts local requests only."}), 403
        for header in ("Origin", "Referer"):
            value = request.headers.get(header)
            if value:
                parsed = urlsplit(value)
                if parsed.scheme not in {"http", "https"} or not _is_local_host(
                    parsed.netloc
                ):
                    # Some browser extensions replace the Origin or Referer on
                    # a legitimate local form submission. The session-bound
                    # CSRF token still proves that the request came from the
                    # VenueView page; requests without it remain blocked.
                    if request.method == "POST" and _has_valid_csrf_token():
                        continue
                    return jsonify({"error": "Cross-origin requests are not allowed."}), 403
        _remove_expired_uploads()
        return None

    @app.before_request
    def enforce_csrf():
        if request.method != "POST":
            return None
        if not _has_valid_csrf_token():
            return jsonify({"error": "The form security token is missing or invalid."}), 400
        return None

    @app.after_request
    def add_local_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'unsafe-inline'; form-action 'self'; "
            "script-src 'self'; object-src 'none'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return _render(
            error="That calendar export is larger than the 25 MB limit.",
            error_code="VV-UPLOAD-413",
            status=413,
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/")
    def index():
        return _render()

    @app.get("/runtime.js")
    def runtime_javascript():
        return Response(RUNTIME_JAVASCRIPT, mimetype="application/javascript")

    @app.get("/support-summary")
    def support_summary():
        status = _rules_status()
        settings_label = {
            "bundled": "Built-in organization settings",
            "imported": "Imported replacement settings",
            "": (
                "Settings need attention"
                if status["state"] == "error"
                else "Standard public settings"
            ),
        }[status["source"]]
        edition = "Private" if packaged_rules_path is not None else "Public"
        latest_code = session.get("last_error_code", "None recorded")
        summary = "\n".join(
            [
                "VenueView Support Summary",
                "=========================",
                f"Version: {__version__}",
                f"Edition: {edition}",
                f"Organization settings: {settings_label}",
                f"Settings status: {status['state']}",
                f"Calendar loaded in memory: {'Yes' if _get_upload_text() else 'No'}",
                f"Latest support code: {latest_code}",
                "",
                "Privacy note: This summary contains no calendar values, filenames, or file paths.",
                "Generated locally by VenueView.",
                "",
            ]
        )
        return Response(
            summary,
            mimetype="text/plain",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="VenueView-support-{__version__}.txt"'
                )
            },
        )

    @app.post("/operational-rules/import")
    def import_operational_rules():
        uploaded = request.files.get("rules_file")
        if uploaded is None or not uploaded.filename:
            return _render(
                error="Choose an organization settings JSON file.",
                error_code="VV-SETTINGS-001",
                status=400,
            )
        raw = uploaded.read(MAX_PRIVATE_RULE_PACK_BYTES + 1)
        if not raw:
            return _render(
                error="The selected settings file is empty.",
                error_code="VV-SETTINGS-002",
                status=400,
            )
        if len(raw) > MAX_PRIVATE_RULE_PACK_BYTES:
            return _render(
                error="The selected settings file exceeds the 1 MB limit.",
                error_code="VV-SETTINGS-003",
                status=400,
            )
        try:
            text = raw.decode("utf-8-sig")
            candidate_pack = load_rule_pack_text(text)
            persist_private_rule_pack(operational_rules_path, text)
        except UnicodeError:
            return _render(
                error="The selected settings file must be UTF-8 JSON.",
                error_code="VV-SETTINGS-004",
                status=400,
            )
        except RulePackValidationError as exc:
            return _render(
                error=f"The organization settings were not changed. {exc}",
                error_code="VV-SETTINGS-005",
                status=400,
            )
        except (OSError, ValueError):
            return _render(
                error=(
                    "The settings file was valid, but VenueView could not save it "
                    "to the private application-data folder."
                ),
                error_code="VV-SETTINGS-006",
                status=500,
            )
        with rules_lock:
            private_rules[0] = candidate_pack
            private_rules_error[0] = ""
            private_rules_source[0] = "imported"
        return _render(
            message="Replacement organization settings were checked, saved, and activated."
        )

    @app.post("/operational-rules/restore-defaults")
    def restore_operational_defaults():
        try:
            restored_pack = (
                load_optional_private_rule_pack(packaged_rules_path)
                if packaged_rules_path is not None
                else None
            )
            remove_private_rule_pack(operational_rules_path)
        except (OSError, UnicodeError, ValueError, RulePackValidationError):
            return _render(
                error="VenueView could not restore the built-in organization settings.",
                error_code="VV-SETTINGS-007",
                status=500,
            )
        with rules_lock:
            private_rules[0] = restored_pack
            private_rules_error[0] = ""
            private_rules_source[0] = "bundled" if restored_pack is not None else ""
        if restored_pack is not None:
            return _render(message="Built-in organization settings were restored.")
        return _render(
            message="Imported organization settings were removed. Standard public settings are active."
        )

    @app.post("/runtime/browser-opened")
    def browser_opened():
        page_id = request.form.get("page_id", "")
        if not _is_valid_page_id(page_id):
            return jsonify({"error": "Invalid VenueView page identifier."}), 400
        with pages_lock:
            active_pages.add(page_id)
            _cancel_pending_shutdown_locked()
        return ("", 204)

    @app.post("/runtime/browser-closed")
    def browser_closed():
        page_id = request.form.get("page_id", "")
        if not _is_valid_page_id(page_id):
            return jsonify({"error": "Invalid VenueView page identifier."}), 400
        with pages_lock:
            active_pages.discard(page_id)
            has_active_pages = bool(active_pages)
        if not has_active_pages:
            _schedule_shutdown_if_no_pages(BROWSER_CLOSE_GRACE_SECONDS)
        return ("", 204)

    @app.post("/quit")
    def quit_venueview():
        _clear_upload()
        with pages_lock:
            active_pages.clear()
            _cancel_pending_shutdown_locked()
        _schedule_shutdown_if_no_pages(SHUTDOWN_RESPONSE_GRACE_SECONDS)
        return Response(
            """<!doctype html><html lang="en"><head><meta charset="utf-8">
            <title>VenueView closed</title></head><body>
            <main><h1>VenueView has closed.</h1>
            <p>You can close this tab and reopen VenueView from its app icon.</p>
            </main></body></html>""",
            mimetype="text/html",
        )

    @app.post("/process")
    def process():
        uploaded = request.files.get("calendar")
        profile_id = request.form.get("profile", "")
        mode = request.form.get("mode", "combined")
        action = request.form.get("action", "preview")
        timezone_name = request.form.get("timezone", "America/New_York")
        window_start_text = request.form.get("window_start", "")
        window_end_text = request.form.get("window_end", "")
        show_rows = request.form.get("allow_sensitive_output") == "on"
        group_multi_location = request.form.get("group_multi_location") == "on"
        _remember_process_form_state(
            profile_id=profile_id,
            mode=mode,
            window_start=window_start_text,
            window_end=window_end_text,
            group_multi_location=group_multi_location,
            allow_sensitive_output=show_rows,
        )

        if action == "clear":
            _clear_upload()
            return _render()

        if uploaded and uploaded.filename:
            try:
                raw = uploaded.read()
                if not raw:
                    raise ValueError("empty upload")
                text = raw.decode("utf-8-sig", errors="replace")
                _remember_upload(text)
            except Exception:
                return _render(
                    error="VenueView could not read that calendar export.",
                    error_code="VV-UPLOAD-001",
                    status=400,
                )
        else:
            text = _get_upload_text()
        if not text:
            return _render(
                error=(
                    "Choose an .ics calendar export, or use the calendar already "
                    "loaded in this session."
                ),
                error_code="VV-UPLOAD-002",
                status=400,
            )
        if profile_id not in profiles:
            return _render(
                error="Choose a valid venue profile.",
                error_code="VV-INPUT-001",
                status=400,
            )
        if mode not in {"detailed", "combined", "both"}:
            return _render(
                error="Choose a valid output mode.",
                error_code="VV-INPUT-002",
                status=400,
            )
        decision_actions = {"separate_combination", "keep_combined"}
        if action not in {"preview", "csv", "excel", *decision_actions}:
            return _render(
                error="Choose a valid action.",
                error_code="VV-INPUT-003",
                status=400,
            )
        if action in {"csv", "excel", *decision_actions} and not show_rows:
            return _render(
                error=(
                    "Acknowledge the privacy notice before using operational "
                    "event data."
                ),
                error_code="VV-PRIVACY-001",
                status=400,
            )
        try:
            start = _date_boundary(window_start_text, timezone_name)
            inclusive_end = _date_boundary(window_end_text, timezone_name)
            if inclusive_end < start:
                raise ValueError("reporting range ends before it starts")
            end = inclusive_end + timedelta(days=1)
            events = parse_ics_text(
                text,
                window_start=start,
                window_end=end,
                default_timezone=timezone_name,
            )
            base_pipeline_result = run_pipeline(
                events,
                profiles[profile_id],
                _effective_rule_pack(),
                group_multi_location=group_multi_location,
            )
        except Exception:
            return _render(
                error=(
                    "VenueView could not process that calendar. The loaded calendar "
                    "remains available for another attempt."
                ),
                error_code="VV-PROCESS-001",
                status=400,
            )
        reviews = combination_reviews(base_pipeline_result)
        valid_review_ids = {review.combination_id for review in reviews}
        if action in decision_actions:
            requested_review_id = request.form.get("combination_id", "")
            if requested_review_id not in valid_review_ids:
                return _render(
                    error="That proposed event combination is no longer available.",
                    error_code="VV-REVIEW-001",
                    status=400,
                )
            _set_separation_override(
                requested_review_id,
                separate=action == "separate_combination",
            )
            action = "preview"
        separate_ids = _get_separation_overrides()
        pipeline_result = apply_separation_overrides(
            base_pipeline_result,
            separate_ids,
        )
        if action in {"csv", "excel"}:
            builder = build_csv_download if action == "csv" else build_excel_download
            try:
                artifact = builder(
                    pipeline_result=pipeline_result,
                    profile_name=profiles[profile_id].name,
                    mode=mode,
                    window_start=window_start_text,
                    window_end=window_end_text,
                )
            except Exception:
                return _render(
                    error=(
                        "VenueView could not create that download. The loaded "
                        "calendar remains available for another attempt."
                    ),
                    error_code="VV-EXPORT-001",
                    status=500,
                )
            return send_file(
                BytesIO(artifact.data),
                mimetype=artifact.mimetype,
                as_attachment=True,
                download_name=artifact.filename,
                max_age=0,
            )
        result = _result_payload(
            events=events,
            pipeline_result=pipeline_result,
            profile_name=profiles[profile_id].name,
            profile_id=profile_id,
            mode=mode,
            window_start=window_start_text,
            window_end=window_end_text,
            show_rows=show_rows,
            group_multi_location=group_multi_location,
            reviews=reviews if mode in {"combined", "both"} else (),
            separate_ids=separate_ids,
        )
        return _render(result=result)

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the local VenueView browser interface"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Loopback port; 0 (the default) selects an available random port.",
    )
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument(
        "--private-rules",
        type=Path,
        help="Optional private rule-pack path outside the application bundle.",
    )
    parser.add_argument("--no-browser", action="store_true")
    return parser


def _schedule_browser_open(address: str, delay: float = 0.8) -> Timer:
    timer = Timer(delay, webbrowser.open_new_tab, args=(address,))
    timer.daemon = True
    timer.start()
    return timer


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not _is_loopback_host(args.host):
        raise SystemExit("VenueView only binds to 127.0.0.1 or localhost.")
    app = create_app(args.config_dir, args.private_rules)
    try:
        from waitress import create_server
    except ImportError as exc:  # pragma: no cover - dependency is packaged
        raise SystemExit(
            "The local UI requires Waitress. Reinstall VenueView with its runtime dependencies."
        ) from exc
    server = create_server(app, host=args.host, port=args.port, threads=4)
    effective_port = int(getattr(server, "effective_port", args.port))
    address = f"http://{args.host}:{effective_port}"
    print(f"VenueView running at {address}", flush=True)
    if not args.no_browser:
        _schedule_browser_open(address)
    app.config["VENUEVIEW_REQUEST_SHUTDOWN"] = server.close
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.config["VENUEVIEW_REQUEST_SHUTDOWN"] = None
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
