# Quick Start

## Install for development

VenueView requires Python 3.10 or newer.

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
```

Activate the virtual environment using the command appropriate for your shell
before running the remaining examples.

## Inspect the synthetic calendar safely

```bash
venueview audit data/synthetic/sample_calendar.ics \
  --window-start 2026-07-17 \
  --window-end 2026-07-20 \
  --profile config/profiles/north_arena_rinks.json \
  --rules config/rules/public_rules.json
```

The audit reports aggregate counts and categories without returning event
titles or source identifiers.

## Generate demonstration rows

```bash
venueview process data/synthetic/sample_calendar.ics \
  --window-start 2026-07-17 \
  --window-end 2026-07-20 \
  --profile config/profiles/north_arena_rinks.json \
  --rules config/rules/public_rules.json \
  --mode combined \
  --allow-sensitive-output
```

`--allow-sensitive-output` is deliberately required because real calendar
titles could be sensitive. Use only the included synthetic file for public
demonstrations.

## Start the local interface

```bash
venueview-ui --config-dir config
```

The application opens in the default browser and binds only to the local
computer. Select the included sample calendar, choose **North Arena — Rinks**,
set July 17–20, 2026, preview the result, review the proposed combination, and
download CSV or Excel output.

## Try a private overlay without committing it

Copy `config/rules/private_rules.example.json` to a location outside the
repository, edit only fictional values, and pass it with `--private-rules` or
import it through the local interface. Do not place operational configuration
or real calendar data inside this project tree.
