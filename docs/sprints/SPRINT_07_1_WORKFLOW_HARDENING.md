# Sprint 07.1 — Workflow Visualization Hardening

## Purpose

Sprint 07.1 closes the verification carryover from Sprint 07 without changing the simulation or comparison contracts. The workflow remains an explanatory view of the active baseline, selected scenario, and returned evidence; it does not infer causality or recommendations.

## Audit scope

The hardening audit covers source, stage, resource-pool, route-option, failure/rework, and SLA overrides; exact visual targeting; duplicate model identifiers; scenario-change summaries; inspector selection and focus restoration; legends; list mode; and absent-result states.

The audit identified three adapter risks before implementation:

1. Backend route probability targets use `routeId:targetId`, while the workflow adapter expected a route ID and option index embedded in the field.
2. Source baseline lookup read only `meanInterarrivalTime`, leaving fixed `arrivalInterval` changes without baseline evidence.
3. Stage baseline lookup omitted `maximumReworkAttempts` and several processing-distribution parameters.

## Acceptance criteria

- Every authorized override resolves its exact baseline scalar or produces a visible warning.
- A route probability change marks only the addressed route edge and never all sibling edges.
- Fixed and Poisson source parameters render their actual baseline values.
- Fixed, exponential, uniform, and triangular processing parameters plus failure probability and maximum rework attempts resolve correctly.
- Unknown and ambiguous targets are excluded from changes and reported as warnings.
- Scenario summaries state the baseline, proposed value, and direction without causal or prescriptive language.
- Closing an inspector restores focus to its originating node; Escape and the close control remain supported.
- Structural, scenario-change, pressure, comparison, and list modes retain visible semantics and result-dependent modes remain disabled before evidence exists.

## Verification mapping

| Evidence | Acceptance covered |
| --- | --- |
| `apps/web/tests/workflow-visualization.test.tsx` adapter cases | Exact source, stage, route, SLA, warning, and target mapping |
| Existing workflow visualization interaction cases | Structure, summaries, disabled evidence modes, selection closure, pressure, comparison, and list mode |
| TypeScript typecheck | Adapter and component contract compatibility |
| Focused web test | Runtime rendering and interaction behavior when the test runner can start |

## Local verification constraints

The single pre-change `pnpm test:web` attempt was blocked before test collection because Vite could not spawn its config helper (`spawn EPERM`). The single root build attempt was blocked by an inaccessible Python isolated-build directory. These directories are intentionally left untouched; permissions, sandbox settings, and checks are not changed. No Git staging, commit, remote, GitHub, Vercel, or deployment action is part of this sprint.
