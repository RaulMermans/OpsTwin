# Sprint 15 — beginner comprehension closure record

## Scope

This record covers presentation-only repairs to the Guided and Advanced web
experience. Simulation formulas, seeds, contracts, rankings, exports, and API
routes remain unchanged.

## Correctness validation

- The quality-stage `failure.probability` is the selection probability for a
  ticket requiring rework. The simulator then follows the configured failure
  route for that selected ticket, subject to maximum rework attempts.
- The canonical support model has a 10% quality rework probability and routes
  selected rework tickets to Level 2. Guided Process wording must therefore
  never say that all tickets enter rework.
- Paired relative deltas are aggregated from per-run paired relative changes.
  They are not necessarily equal to a percentage derived from displayed
  aggregate means. The UI labels this `Average paired relative change`.

## Implemented presentation repairs

- Landing and setup lead with the fictional customer-support problem,
  beginner-first process names, and the motivation for the two default
  changes.
- Guided result cards show average change, matched-test counts and percentage,
  plausible range of the average change, explicit inconclusive wording, and
  metric-direction-aware comparative text.
- Evidence navigation is unavailable until a successful comparison. Guided
  Process list wording removes operational identifiers and explains selected
  rework tickets accurately.
- Team workload, Uncertainty, sensitivity, Costs, playback, and Advanced
  ranking wording were simplified without recalculating backend evidence.
- The Process content/canvas/grid now explicitly stretches to available width
  and keeps its deliberate internal map width above the mobile list fallback.

## Verification status

- Direct web TypeScript check (`tsc --noEmit`): passed.
- Direct web ESLint (`eslint . --max-warnings=0`): passed.
- `git diff --check`: passed.
- Focused Vitest process started under Node 22.22.3 but this managed runner
  returned no completion summary. It is not recorded as a passing gate.
- Rendered desktop/mobile measurements, manual desktop QA, screenshots,
  deployment, smoke verification, and production QA remain pending. Manual
  mobile QA was not performed.

## Claim boundary

No participant study, production deployment, screenshot refresh, commit, or
push is claimed by this local checkpoint. Those actions require the full test
and browser gates to complete successfully.
