# Demonstration Combination Rules

All rules in this repository are fictional. Their names, thresholds, locations,
and program terms are designed to exercise the engine and do not represent any
organization's scheduling policy.

## Model

Classification rules assign a group and function to matching events. Ignore
rules remove explicitly unwanted categories. Combination rules may then merge
compatible event occurrences when every declared condition is satisfied.

A combination rule can constrain:

- Normalized title, group, function, venue, and location
- Maximum time gap, including the exact boundary
- Same-day behavior
- Location conflicts occurring between candidate blocks
- Title prefixes or normalized-title variants

The engine preserves the source components and generates a review record for
every automatic multi-occurrence merge. A reviewer can keep the proposal or
restore the separate events for the current in-memory session.

## Included examples

| Rule | Intent | Maximum gap |
|---|---|---:|
| `combine_summit_skills_blocks` | Merge adjacent Summit Skills blocks only on the same rink with matching group/function | 15 minutes |
| `combine_summit_skills_full_name_blocks` | Handle synthetic title variations after normalization | 15 minutes |
| `combine_same_title_north_arena_hockey_blocks` | Merge same-title hockey blocks only on the same North Arena rink | 10 minutes |
| `combine_same_title_same_location_events` | Demonstrate a conservative same-title/location fallback | 15 minutes |

An incompatible event occupying the same location during a gap blocks the
merge. Events on different rinks do not interfere with one another.

## Multi-location source events

Separately from time-based combination, the interface can group one source
occurrence assigned to several calendar locations into a single row displaying
the complete location set. This option is off by default. It groups only the
location assignments of that one occurrence; it does not merge unrelated
events that happen to share a title.

## Rule-pack separation

`config/rules/public_rules.json` is the demonstration pack.
`config/rules/private_rules.example.json` documents the overlay schema using
placeholders. A real overlay belongs in per-user application data or another
ignored location outside the repository.

The public pack always loads first. An explicitly selected private overlay can
replace or extend it after validation. Packaging scripts exclude overlays from
public builds unless a builder deliberately selects the private edition and
provides an external source file.

## Known limits

Rules are deterministic pattern matching, not semantic understanding. They do
not infer organizational intent, resolve resource conflicts, or prove that a
merge is operationally correct. Rule authors and output reviewers remain
responsible for validation.
