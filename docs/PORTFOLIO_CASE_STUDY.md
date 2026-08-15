# Portfolio Case Study

## The problem

While working for the New York State Olympic Regional Development Authority
(ORDA) at the Lake Placid Conference Center, the creator encountered a shared
events calendar containing far more information than one venue team needed for
weekly operations. Preparing function sheets meant repeatedly filtering the
calendar, expanding recurring events, separating room and rink assignments,
deciding when adjacent blocks belonged together, and copying the result into
Excel. The manual process consumed focused staff time and made the reason for
each inclusion or grouping difficult to audit.

## The response

VenueView began as an automation for the creator's own function-sheet workflow
and developed into a local desktop application that coworkers could use. The
application converts a calendar export into a venue-specific, reviewable event
stream and generates editable CSV and Excel deliverables. Configuration files
separate venue selection and operational policy from the processing engine, so
the same architecture can serve different facility types without embedding
private rules in public code.

## Engineering choices

- Local-first processing keeps source calendars off hosted services.
- A field allowlist excludes descriptions, contacts, organizers, attendees,
  URLs, and attachments.
- Bounded recurrence expansion avoids unbounded calendar processing.
- Explicit JSON rules make classifications and combinations testable.
- Human review remains in the loop for ambiguous records and automatic merges.
- Formula neutralization protects spreadsheet exports from untrusted text.
- Public/private packaging boundaries keep operational configuration out of
  the portfolio repository.

## Real-world adoption

The creator used the original application to produce Excel function sheets for
Conference Center operations. The tool continued to be used by a supervisor
and coworkers after that initial personal workflow. VenueView installers were
submitted to ORDA IT and whitelisted for use on the internal network. The
creator also led an approximately 45-minute presentation and user walkthrough
for roughly 20 staff members, explaining the problem, design, workflow, and how
to operate the application. Interest from leadership responsible for Olympic
Center operations supported exploration beyond the original department and
facility context. This interest is not presented as confirmed Olympic Center
deployment.

These are qualitative adoption signals. No private usage analytics are included
in this repository, so the case study intentionally makes no unsupported claim
about exact hours saved, error reduction, number of departments deployed, or
financial impact.

## Effect on the work

For the creator, VenueView shifted function-sheet preparation from repetitive
calendar filtering and transcription toward reviewing structured output. For
coworkers, it made the workflow repeatable through a guided local interface and
produced a common spreadsheet format. For supervisors, the rule-based review
path made automated groupings visible rather than hiding them inside a script.

## What is safe to show

- The public source and its commit history beginning with the sanitized tree
- Architecture, security boundary, tests, and packaging approach
- Fictional venue profiles, rules, sample calendar, screenshots, and outputs
- The verified adoption narrative above, using public organization and facility
  names without identifying staff or revealing internal configuration
- A live demonstration using `data/synthetic/sample_calendar.ics`

Do not show real calendar exports, function sheets, internal taxonomies, private
rules, email threads, staff names, internal network details, real installers,
or unapproved employer branding.

## Suggested résumé bullet

> Built and deployed a local-first Python calendar-processing application that
> transforms recurring, multi-location `.ics` data into reviewable Excel
> function sheets; adopted by coworkers, reviewed for use in a managed internal
> environment, and presented in a 45-minute walkthrough to approximately 20
> staff members.

The organization name supplies useful context but does not imply endorsement.
If space is limited, remove the presentation detail before removing the
technical result or adoption evidence.

## Suggested LinkedIn description

> VenueView grew from a repetitive operations problem I encountered while
> working for ORDA at the Lake Placid Conference Center: turning a large shared
> calendar into the focused weekly function sheets staff actually needed. I
> designed a local-first Python pipeline for recurrence expansion, venue
> filtering, explicit classification and combination rules, human review, and
> safe Excel export. The original tool moved beyond my own workflow to continued
> use by coworkers and a supervisor, and I led a 45-minute user walkthrough for
> approximately 20 staff members. This public portfolio edition preserves the
> engineering while replacing all executable venue configuration, events,
> rules, and outputs with fictional demonstration data.
