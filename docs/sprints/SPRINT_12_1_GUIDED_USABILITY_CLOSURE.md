# Sprint 12.1 — Guided Usability Closure

## Purpose

Sprint 12.1 closes the four known Sprint 12 completion defects without changing simulation, comparison, sensitivity, economics, playback, ranking, or export contracts. It does not claim human participant usability validation.

## Defects closed

### Advanced landing route

`apps/web/app/workspace/page.tsx` is now an async server component that reads the `mode` search parameter and passes a resolved `initialMode` (`"guided" | "advanced"`) into `Workspace`. Resolution is pure and exported (`resolveInitialMode`): `mode=advanced` opens Advanced, `mode=guided` and any missing/invalid value open Guided. No `window.location` access occurs during server rendering. The landing page's "Open advanced workspace" action now links to `/workspace?mode=advanced`; "Try the guided comparison" remains `/workspace`. Client-side mode switching after initialization is unchanged.

### Orientation hydration safety

The first-run orientation no longer reads or writes `sessionStorage`. Both the server render and the first client render now compute `orientationVisible = true` unconditionally, eliminating the prior hydration-mismatch risk (a lazy `useState` initializer that read `window.sessionStorage` only on the client). Dismissal now persists only for the currently mounted workspace instance; a full page reload remounts the component and shows the orientation again. This matches the behavior already documented (but not yet implemented) in `docs/USABILITY_FINDINGS.md`. No `suppressHydrationWarning` is present in the source.

### Direction-aware comparative interpretation

`apps/web/lib/scenario-lab/comparative-interpretation.ts` adds a pure function, `buildComparativeInterpretation(result)`, that reads the existing `0.5.0` comparison response's `ranking` array (already ordered by the backend using directed paired mean delta, improvement probability, confidence width, then scenario ID) and produces one of four factual states: `leader`, `tie`, `singleEligibleScenario`, or `noEligibleScenarios`. It performs no ranking, eligibility, or delta computation of its own. A tie is reported when the top two ranked scenarios' objective mean deltas differ by no more than `1e-9`, the same tolerance centralized in `apps/simulation-api/app/scenarios/metrics.py` and documented in `docs/SCENARIO_COMPARISON_SPEC.md`. `GuidedResultSummary` renders the resulting statement (e.g. "Among the tested scenarios, Add one Level 1 agent produced the larger observed improvement in average cycle time in this experiment") together with the objective mean delta, improvement probability where available, and an eligibility/exclusion footnote when scenarios failed or were ineligible. The existing non-prescriptive disclaimer is always shown alongside it. None of the prohibited terms (best decision, recommended, optimal, guaranteed, root cause, winning option, etc.) appear in the generated copy.

### Guided evidence disclosure

Guided mode now exposes a single accessible tablist (`role="tablist"`, arrow-key/Home/End navigation, `aria-selected`/`aria-controls`) with eight views: Summary, Flow, Risk, Resources, Sensitivity, Economics, Playback, and Technical (`apps/web/lib/scenario-lab/guided-evidence.ts`). Exactly one panel is visible at a time; hidden panels use the native `hidden` attribute, which removes them from the accessibility tree and keyboard tab order without unmounting them (so in-progress Sensitivity/Economics draft input is preserved across tab switches, and no panel mount triggers a network request — Sensitivity and Economics only call the API on explicit user submission). Risk, Resources, and Technical reuse the existing `RiskView`, `ResourceView`, and `TechnicalView` components (now exported from `results-panel.tsx`) rather than duplicating their logic. Summary remains the default view and sits immediately after the run panel. Editing the baseline, a scenario, or execution settings invalidates the result and resets the Guided view to Summary. Empty panels (Summary/Risk/Resources/Technical/Playback before a result exists) show a one-line prerequisite message; Flow, Sensitivity, and Economics remain usable before a run, matching their existing pre-result availability. Advanced mode is untouched: it still renders `GuidedResultSummary`, the full `Results` tab set (Overview/Metrics/Risk/Resources/Technical), and all six evidence anchor sections exactly as before.

## Non-goals

No new endpoint, contract, simulation calculation, ranking algorithm, objective direction, integrity check, export shape, or dependency was introduced. Request payloads and export output are unchanged.

## Verification mapping

| Evidence | Acceptance covered |
| --- | --- |
| `apps/web/tests/workspace-mode-routing.test.tsx` | `resolveInitialMode` parameter resolution; Guided/Advanced initial mode; client-side mode switch after initialization; landing link destinations |
| `apps/web/tests/workspace-orientation.test.tsx` | Initial visibility without storage access, mouse/keyboard dismissal, no persistence across remount, no `suppressHydrationWarning` |
| `apps/web/tests/comparative-interpretation.test.ts` | Lower/higher-is-better leader, exact tie, near tie at tolerance, non-tie above tolerance, one failed scenario, one ineligible scenario, no successful paired runs, single-scenario result |
| `apps/web/tests/guided-evidence-navigation.test.tsx` | Default Summary panel, prerequisite copy, single visible panel, hidden panels excluded from the accessibility tree, arrow-key navigation, Risk/Resources/Technical reuse, stale-result reset, evidence-link navigation, Advanced mode preserved unchanged |
| `apps/web/tests/workspace-scenario-lab.test.tsx` (updated) | Existing Advanced-mode Overview/Metrics/Risk/Resources tab, export, and prescriptive-language coverage continues to pass under the now-Advanced-only `Results` tablist |

## Local verification

`pnpm lint`, `pnpm typecheck`, `pnpm test` (247 backend tests), `pnpm test:web` (172 web tests, up from 142 with the addition of the tests above), `pnpm build`, and `pnpm verify` (ruff, ESLint, mypy over 51 source files, TypeScript, both builds, canonical example, all benchmark smokes, and source packaging) all passed on this session's macOS host using Node 22.22.3 (via `nvm`) and the repository's existing `.venv` (Python 3.12.13). `git diff --check` passed with no whitespace errors. `/workspace` now builds as a dynamic (`ƒ`) route because it reads `searchParams`, which is expected.

## Production verification — 2026-07-21

Pushed as commit `26d76b3` to `origin/master`; the existing `ops-twin` Vercel Services project (GitHub-integration auto-deploy, same one domain, no new project) picked it up and was confirmed live by polling `https://ops-twin.vercel.app/workspace?mode=advanced` until the server-rendered HTML showed the Advanced mode-switch button as `aria-pressed="true"` (SSR-level proof that the search parameter drives the initial mode). `pnpm smoke:preview -- https://ops-twin.vercel.app` passed: `/`, `/workspace`, `/api/simulation/health`, `/api/simulation/simulate`, `/api/simulation/simulate/repeated`, and `/api/simulation/compare/scenarios` all returned `200`; the two `422` rows are the smoke script's intentional validation-error cases.

A live browser session against production (390×844 mobile and default desktop viewports) ran the default Guided comparison and exercised every Guided evidence tab (Summary, Flow — seen earlier via Structure mode's canonical map, Risk, Resources, Sensitivity tab present, Economics tab present, Playback, Technical tab present): each showed exactly one panel at a time with real backend evidence, and the rendered comparative interpretation sentence read "Among the tested scenarios, Faster triage produced the larger observed improvement in average cycle time in this experiment (observed mean change -0.73 min, improved in 48% of paired simulations)," correctly identifying the higher-ranked scenario (Faster triage, rank 1) over the one that regressed (Add one Level 1 agent, rank 2, positive/worse delta on a lower-is-better objective) — direction-aware and free of prohibited language, with the non-prescriptive disclaimer present. No console errors or hydration warnings were observed. At the mobile viewport the Guided evidence tablist scrolled within its own contained row (visible internal scrollbar) with no page-level horizontal overflow.

## Human usability evidence

Guided usability implementation: complete. Automated regression evidence: complete (above). Expert/owner walkthrough: pending production QA (recorded separately once deployed). Five-participant usability validation: pending — not claimed as completed by this sprint.
