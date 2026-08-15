# Limitations

VenueView's boundaries are part of its design and should be stated plainly in
portfolio discussions.

## Product boundaries

- It reads exported `.ics` files; it does not connect to, edit, or synchronize
  a live calendar.
- It prepares operational schedules; it is not the authoritative scheduling or
  resource-booking system.
- It does not detect every double booking or resolve staffing, equipment, or
  venue conflicts.
- It does not read descriptions, so setup and equipment fields remain blank for
  staff completion.
- It does not use machine learning or infer intent. Classification and merging
  depend on explicit, testable rules.
- It does not provide remote access, shared sessions, accounts, roles, or a
  central database.
- One user must review uncertain records, combination proposals, and all final
  exports before operational use.

## Calendar-format limits

- RFC 5545 recurrence support is intentionally bounded by the selected date
  window and safety limits.
- Vendor-specific properties outside the allowlist are ignored.
- Unusual timezone definitions or malformed exports may require review.
- Multi-location grouping relies on the source export representing locations
  consistently.

## Configuration limits

- Venue profiles select known taxonomy paths; they are not an administrative
  editor for arbitrary venue models.
- Profiles and rules are JSON files. Changing the organizational model requires
  editing and validating those files, then rerunning tests.
- Rule thresholds are policy inputs, not universal truths. The public values
  are fictional and unsuitable for a real deployment without review.
- Private overlays can change behavior and therefore need their own change
  control and regression cases.

## Security and distribution limits

- Loopback-only HTTP reduces exposure but does not protect against malicious
  software already running as the same OS user.
- The public source does not provide centralized authentication, encryption at
  rest, audit logging, or managed update delivery.
- A successful build or checksum does not establish publisher identity.
  Production installers still require signing, notarization where applicable,
  endpoint-security review, and clean-machine testing.
- The repository is a portfolio candidate, not an employer-supported public
  release.

## Evidence limits

The codebase demonstrates engineering choices and a real adoption story, but it
does not contain private usage analytics. Portfolio statements should therefore
use verifiable facts—continued use, installer review, a staff walkthrough, and
known users—without inventing time savings, error-rate reductions, revenue, or
organization-wide deployment counts.
