# Privacy and Data Boundary

## Public repository policy

| Material | Public status |
|---|---|
| Source code and generic architecture | Allowed |
| Fictional venues, events, rules, and expected outputs | Allowed |
| Real calendar exports, titles, UIDs, schedules, or generated reports | Prohibited |
| Internal venue taxonomy or operational thresholds | Prohibited |
| Contacts, descriptions, URLs, attachments, organizers, or attendees | Prohibited |
| Employer documents, screenshots, recordings, installers, or private history | Prohibited unless separately reviewed and approved |

The profiles, taxonomy, rules, and samples committed here are fictional. Public
screenshots, videos, and demonstrations must use only this synthetic material
or independently created equivalents.

## Parser boundary

The parser allowlists fields required for scheduling and grouping. It does not
ingest descriptions, contacts, URLs, attachments, organizers, or attendees.
Audit reports emit aggregate structure and omit titles and source UIDs.

## Output boundary

Operational previews and downloads can contain source titles, so both the CLI
and interface require a deliberate privacy acknowledgement. CSV and Excel files
are generated in memory, source UIDs are omitted, and formula-like text is
neutralized before spreadsheet export.

The local interface holds a decoded calendar in process memory under an opaque
session token. Uploads are capped at 25 MB, expire after 30 minutes of
inactivity, and can be removed immediately with **Clear loaded calendar**. The
service does not intentionally save uploads to the project, an output folder,
or a database.

## Public/private configuration

The public rule pack contains only fictional demonstrations. Optional private
overlays are validated and stored outside the repository in per-user
application data. Public packaging uses allowlists and rejects bundled private
rules unless the builder explicitly chooses a private build and supplies a file
outside the project tree.

## Repository controls

`.gitignore` blocks calendar exports, spreadsheets, media, output directories,
private configuration, and environment files while allowing the named
synthetic fixture. Automated safety tests verify the fictional configuration
markers and disallowed artifact types.

A public repository should start from a reviewed, history-free tree. Removing a
sensitive file in a later commit is not enough because it remains in Git
history.

## Residual risk

Calendar titles and UIDs remain sensitive even though high-risk fields are not
parsed. Another process running under the same operating-system account may be
able to inspect memory or automate the browser. VenueView is therefore a
single-user, loopback-only utility rather than a hosted or multi-user service.
