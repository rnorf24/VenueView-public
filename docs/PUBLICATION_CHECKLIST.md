# Public Repository Checklist

Do not change repository visibility until every required item is complete.

## Source and history

- [ ] Repository was initialized from this sanitized tree, not cloned with the
  private repository's history.
- [ ] No private remote, fork relationship, tags, branches, issues, releases,
  Actions artifacts, or Git LFS objects were copied.
- [ ] The first commit contains only reviewed public files.
- [ ] Branch protection and secret scanning are enabled where available.

## Content

- [ ] Full case-insensitive scans find no unapproved organization, room,
  program, person, client, calendar-provider, or internal-system identifiers;
  intentional references are limited to ORDA and publicly advertised top-level
  facilities in the project narrative.
- [ ] No real `.ics`, spreadsheet, PDF, screenshot, video, installer, log,
  report, or function sheet is tracked.
- [ ] All committed profiles have `pilot_status: demonstration`.
- [ ] All rules, events, dates, thresholds, identifiers, and expected outputs
  are demonstrably fictional.
- [ ] Image and document metadata have been inspected.
- [ ] README claims match evidence and do not imply endorsement of the public
  repository.

## Engineering validation

- [ ] `python -m compileall -q src tests packaging` passes.
- [ ] `python -m pytest` passes in a clean environment.
- [ ] The synthetic audit and process commands in the README succeed.
- [ ] Generated combined output matches the committed expected fixture.
- [ ] A clean source distribution contains no ignored/private material.
- [ ] Dependency and secret scans have been reviewed.

## Legal and presentation decisions

- [ ] Confirm source ownership and any employment-agreement obligations.
- [ ] Decide deliberately between all-rights-reserved and an open-source
  license; do not add a license casually.
- [ ] Obtain approval before using an employer's name, logos, screenshots,
  quotes, staff identities, or claims of endorsement.
- [ ] Record whether public distribution of compiled installers is allowed.
- [ ] Prepare only synthetic screenshots and demo output.

## GitHub and portfolio polish

- [ ] Add repository description, topics, social preview, and a concise About
  link.
- [ ] Enable CI for tests and the public-safety check.
- [ ] Create a `1.0.0-rc.3` source release only after validation.
- [ ] Pin the repository on the GitHub profile.
- [ ] Link it from LinkedIn and résumé using the wording in
  `PORTFOLIO_CASE_STUDY.md`.

## Final two-person review

Ideally, one person other than the author should inspect the exact first commit
and release archive for confidential residue. Record the reviewed commit hash
and archive SHA-256 before making the repository public.
