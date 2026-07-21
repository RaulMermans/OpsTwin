# Changelog

All notable changes to OpsTwin are recorded here. Dates use the sprint
checkpoints recorded in `SCRATCHPAD.md` and `docs/sprints/`.

## Unreleased

Public repository and portfolio preparation (Sprint 13): case-study README,
repository governance files (`SECURITY.md`, `CONTRIBUTING.md`, this file),
production screenshots, a public claim register, a portfolio content pack,
and a deterministic public-release verifier. No analytical or simulation
behavior changed. Repository visibility, license selection, and a release
tag remain pending owner approval.

## 1.0.0 — Prepared, not tagged

The product surface below is implemented, deployed to production, and
verified, but **no `v1.0.0` Git tag or GitHub Release has been created**.
This entry documents what a first release would contain if one is cut.

- Discrete-event simulation engine with deterministic seeding (SimPy).
- Repeated stochastic execution with online aggregation and representative
  run selection.
- Paired scenario comparison with common random numbers, confidence
  intervals, improvement probabilities, risk classification, and guardrails.
- Read-only workflow (Flow) visualization with change and evidence overlays.
- One-factor-at-a-time sensitivity analysis.
- Explicit-assumption economic comparison and economic sensitivity.
- Deterministic client-side representative-run playback.
- Guided no-edit comparison flow (default) and an Advanced scenario-editing
  workspace.
- JSON/CSV exports and automated integrity validation.
- One-repository, one-Vercel-Services-project production deployment
  (`https://ops-twin.vercel.app`).

## Pre-1.0 sprint history

See `docs/ROADMAP.md` for the full sprint-by-sprint status list and
`docs/sprints/` for each sprint's detailed record, from Sprint 00
(deterministic foundation) through Sprint 12.1 (guided usability closure).
