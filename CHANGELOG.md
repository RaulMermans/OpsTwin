# Changelog

All notable changes to OpsTwin are recorded here. Dates use the sprint
checkpoints recorded in `SCRATCHPAD.md` and `docs/sprints/`.

## Unreleased

Codegeist CG-3: platform-independent calibration (`cal.1.0.0`) from operational snapshots to Core `0.2.0` models, identifiability and assumption gates, generative holdout, synthetic fixture remote at `POST /api/integrations/atlassian/v1/calibrate`. Compare remains synthetic-only. Live Jira snapshots are not calibrated remotely.

Codegeist CG-2: versioned operational snapshot `os.1.0.0`, Jira/JSM bounded ingest with provenance and data quality, seeded synthetic lab, and an Operational Data section in the Forge Custom UI. Snapshots are not sent to the simulation remote. Public `/api/simulation/*` contracts are unchanged.

Codegeist CG-1: FIT-authenticated synthetic comparison adapter at `POST /api/integrations/atlassian/v1/compare`, Forge Remote compute egress, JSM request-type resolver, and CG-0 security-defect closure. Public `/api/simulation/*` contracts are unchanged.

Codegeist CG-0: isolated `apps/atlassian-forge` foundation, Atlassian integration docs, and Forge skills/MCP project config. No Core simulation contract changes.

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
