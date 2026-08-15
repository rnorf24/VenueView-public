# Export Behavior and Workbook Mapping

## Browser actions

VenueView processes the uploaded calendar in memory and supports three actions:

| Action | Result |
|---|---|
| Preview results | Local operational table, limited to 250 rows |
| Download CSV | One selected CSV, or a ZIP with Detailed, Combined, and Review CSV files in Both mode |
| Download Excel | Weekly Function Sheet plus audit-oriented workbook tabs |

Operational previews and downloads require the privacy acknowledgement. No
source UID is exported.

When a reviewer chooses **Keep events separate** for a proposed combination,
the effective separated event stream is used by the Function Sheet, Combined
CSV, Combined workbook tab, and summary row counts. Choosing **Keep as one
event** restores the rule-generated combined stream. These choices last only
for the current in-memory calendar session.

## Excel workbook

The workbook contains:

1. **Function Sheet** — selected weekly operational view. Detailed mode uses
   detailed rows; Combined and Both use combined rows.
2. **Summary** — profile, window, row counts, exclusions, and review count.
3. **Detailed** — included in Detailed and Both modes.
4. **Combined** — included in Combined and Both modes.
5. **Review** — detailed rows with one or more review reasons.

The Function Sheet recreates the generic structure observed in the private
reference without copying any source content. Its columns are:

```text
Time | Location | Group | Function | Set-up | HT | P/M | Pro | Lav | HH Mic | Flip
```

Set-up and equipment fields are intentionally blank and editable. VenueView
does not infer these needs from event descriptions because descriptions are
outside the approved parser boundary.

When an event has no classified group, the Function Sheet uses its title as the
Group fallback. Function uses the classified function when available and the
title otherwise. This provisional mapping needs operational approval.

## Safety properties

- Source uploads and generated files are not retained by the local service.
- Calendar UIDs are excluded from downloads.
- Formula-like text is prefixed so spreadsheet applications treat it as text.
- Workbooks carry a visible review notice and are not labeled as approved.
- Real source workbooks and generated operational outputs remain Git-ignored.
