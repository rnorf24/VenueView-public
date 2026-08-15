# VenueView Security Boundary

VenueView is designed as a local desktop utility, not a network service. The
security controls in the current local prototype are deliberately small and
auditable:

- The server accepts only `127.0.0.1` and `localhost` Host values.
- The packaged server uses Waitress and binds to loopback. Wildcard hosts are
  rejected by the launcher.
- The default port is randomly selected by the operating system instead of
  assuming a shared, predictable port.
- POST forms require a random CSRF token held in an HttpOnly, SameSite=Strict
  session cookie. Local `Origin`/`Referer` values are checked when browsers
  send them.
- Responses are uncached and include CSP, frame, referrer, MIME-sniffing,
  cross-origin, and permissions headers.
- Multipart uploads are capped at 25 MB and use an in-memory request stream.
- A source calendar is held under an opaque per-session token, limited to a
  small number of active sessions, and expired after 30 minutes without use.
  The Clear button removes it immediately. The process does not write the
  source calendar to the project, an output folder, or a database.
- The signed, HttpOnly local session remembers only the selected public profile
  identifier, event-view mode, reporting dates, and boolean interface choices.
  It never stores calendar contents, event titles, filenames, or feed URLs.
- Combination review decisions are held only alongside that in-memory upload.
  They contain opaque combination identifiers rather than source UIDs and are
  cleared when the upload is replaced, cleared, expired, or the app exits.
- The final VenueView page notifies the loopback service when it closes; after
  a short refresh/navigation grace period, the process exits and its in-memory
  calendar is discarded. **Quit VenueView** performs the same cleanup
  explicitly.
- The lifecycle helper is a fixed same-origin script. It cannot read arbitrary
  files, and its POST requests remain protected by the session CSRF token and
  loopback request checks.
- CSV and Excel downloads are generated in memory and require an explicit
  privacy acknowledgement.
- Desktop release scripts launch the newly bundled executable and require its
  loopback `/health` endpoint to respond before creating installer artifacts.
- Each installer directory receives a SHA-256 checksum file and a
  machine-readable release manifest so accidental corruption can be detected.
- Imported private operational rule packs are validated before activation and
  stored in a per-user application-data file outside the source tree.
- Approved internal private builds may carry one validated default rule pack.
  Public builds reject and omit that pack, and imported replacements continue
  to live outside the installed application.
- Installer specifications and source-package manifests allowlist public
  configuration files instead of recursively copying the config directory.
  Private packaging requires an explicit edition flag and a source path outside
  the project tree.

## What this does not provide

The loopback boundary is not a substitute for operating-system security. A
malicious process already running as the same user can read local memory,
automate the browser, or interact with the loopback port. The app does not
provide multi-user authentication, remote access, encryption for the local
HTTP hop, endpoint management, or signed update delivery.

Before final staff distribution, the release must complete:

1. Windows Authenticode signing and timestamping through the fail-closed
   production build path.
2. Apple Developer ID signing and notarization through the fail-closed
   production build path.
3. A documented update/rollback path and dependency vulnerability review.
4. Clean-machine tests confirming that the bundles do not require Python.
5. A review of private rule overlays and generated-file retention by the
   organization that owns the calendar data.

The GitHub-generated installers are unsigned evaluation artifacts. Production
artifacts are built separately on protected signing machines, and their release
manifests record the verified trust state.
Successful compilation, a passing health check, and a matching checksum confirm
build integrity; they do not establish publisher identity or replace code
signing, Apple notarization, endpoint-security review, or clean-machine testing.

Never change the launcher to bind `0.0.0.0` or another LAN address without a
new threat model, authentication design, and explicit operational approval.
