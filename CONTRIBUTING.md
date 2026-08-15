# Contributing to VenueView

VenueView's public repository is a portfolio-safe engineering record. Every
change must preserve the project's privacy boundary.

## Never commit

- Real calendar exports or converted calendar data
- Client, staff, attendee, organizer, or contact information
- Agreements, private workbook templates, screenshots, or recordings
- Generated operational reports, function sheets, review files, or exports
- Credentials, personal access tokens, API keys, signing keys, or `.env` files
- Private rule keys or organization-only configuration

Use `data/synthetic/` for fabricated test cases and `config/rules/public_rules.json`
for portfolio-safe examples. Approved private rules belong outside this public
repository in an ignored `config/private/` directory.

## Before proposing a change

1. Review the intended files and confirm they belong in the public project.
2. Run `python -m pytest`.
3. Confirm that privacy tests pass.
4. Update `CHANGELOG.md` and the relevant focused document when behavior,
   security, packaging, or an architectural decision changes.
5. Keep implemented, planned, and stakeholder-pending features clearly
   distinguished in documentation.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
```

GitHub Actions repeats the test suite on Linux, Windows, and macOS for every
push and pull request.
