# Validation

Run these checks from the repository root in a clean Python 3.10+ environment.

## Automated checks

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m compileall -q src tests packaging
python -m pytest
```

The test suite covers parsing, recurrence behavior, profiles, rules,
combination boundaries, review decisions, CSV/Excel exports, formula
neutralization, local-web security controls, packaging constraints, and public
safety markers.

## Demonstration workflow

```bash
venueview audit data/synthetic/sample_calendar.ics \
  --window-start 2026-07-17 \
  --window-end 2026-07-20 \
  --profile config/profiles/north_arena_rinks.json \
  --rules config/rules/public_rules.json

venueview process data/synthetic/sample_calendar.ics \
  --window-start 2026-07-17 \
  --window-end 2026-07-20 \
  --profile config/profiles/north_arena_rinks.json \
  --rules config/rules/public_rules.json \
  --mode combined \
  --allow-sensitive-output
```

Compare the combined rows with
`data/synthetic/expected_north_arena_rinks_combined.json`.

## Public-safety inspection

Before publishing, inspect filenames and file contents for real identifiers,
email addresses, phone numbers, internal URLs, usernames, local file paths, and
unexpected binary artifacts. Confirm that only the named fixture under
`data/synthetic/` uses a calendar extension and that no spreadsheets, media,
installers, archives, caches, or virtual environments are included.

## Distribution gates

Passing tests is necessary but does not approve public release of compiled
installers. Signing, notarization, endpoint review, clean-machine acceptance,
license selection, and employer-attribution approval are separate gates.

Record the final commit hash, archive SHA-256, Python version, operating system,
and test result when publishing a release.
