# Sprint 14 — Plain-language and Flow closure

## Scope

This sprint repairs the Flow layout and makes the existing Guided comparison
more understandable without changing simulation formulas, requests,
responses, ranking, exports, or analytical capabilities.

## Local implementation record

- Root cause: `.workflow-content` allowed its canvas grid track to shrink to
  zero while `.workflow-grid` required a 720px minimum; `.workflow-canvas`
  then hid overflow. The change summary also lived outside the layout grid.
- The repair makes the summary, map, and inspector explicit layout tracks;
  protects the desktop canvas minimum; stacks at tablet widths; and uses a
  contained canvas scroll rather than hidden content where needed.
- Guided labels, field help, result range wording, percentage-point
  formatting, result-reading help, and evidence-tab names are presentation
  only and centralize metric language in `metrics.ts`.

## Verification status

`pnpm typecheck` passed with Node 22.22.3. A targeted Vitest invocation
reported 100 passing tests but exited non-zero because nine fork workers
timed out at startup; it is not recorded as a passing gate. Browser, manual,
production, screenshot, commit, push, and deployment checks remain pending.

## Sprint 14.1 closure attempt — 2026-07-22

- Guided settings, Process, Test assumptions, Costs, and the glossary now use
  business-first labels while Advanced keeps the existing technical labels.
- Paired deltas now route through the central metric formatter, including
  percentage points for proportion deltas. The Guided conclusion distinguishes
  a higher average from the returned plausible-range interpretation.
- Local acceptance is blocked before Vitest collection: Vite's installed
  `picomatch@4.0.5` throws `TypeError: parse.fastpaths is not a function`.
  A frozen, forced `pnpm install` reported the lockfile up to date and did not
  repair the installed parser. Consequently no browser, owner QA, deployment,
  screenshot, package, or production claim is recorded for this attempt.
