# Codegeist sprint map

Hackathon start 2026-10-27; internal freeze 2026-12-18; submit 2026-12-21.

| Sprint | Objective |
|---|---|
| CG-0 | Foundation and feasibility |
| CG-1 | Forge application identity and secure remote integration |
| CG-2 | Jira/JSM data ingestion and normalization |
| CG-3 | Operational model calibration |
| CG-4 | AI transformation interventions (adapters, not new math) |
| CG-5 | Native Atlassian product experience |
| CG-6 | Decision intelligence and economics in Jira |
| CG-7 | Evaluation, security, hardening |
| CG-8 | Release, storytelling, submission |

## CG-1 implementation specification

**Objective:** Registered OpsTwin Forge app installed on `opstwin-dev.atlassian.net` / OPS, plus an authenticated Forge Remote that can run a **synthetic** comparison without forwarding issue text.

**Dependencies:** Owner `forge login`; Developer Space; `forge register` replacing the placeholder ARI; owner approval if hosting the Remote off-workstation.

**Deliverables:** real `app.id`; `remotes` + `endpoint` in manifest; FIT-verified development endpoint; egress allowlist; latency notes; no production API mutation unless a dedicated route is approved.

**P0:** register, deploy, install, queue page visible, FIT reject/accept tests against the hosted verifier (can still use synthetic JWT keys plus one live invoke).  
**P1:** first live `asUser` project GET.  
**P2:** second-site install test.

**Implementation:** Python adapter on the existing FastAPI service (ADR-024). Custom UI remains a function resolver; comparison uses `invokeRemote`.

**Acceptance:** `forge_live_installation_status=pass`; at least one FIT-authenticated Remote call; Core `pnpm verify` still green.

**Tests:** extend fit tests with hosted JWKS mock; contract that Remote body is a comparison request, not Jira issues.

**Live verification:** OPS queue page screenshot/URL; `forge install list`; Remote 401 without token.

**Bottleneck:** 25s timeout and comparison work budget.

**Contingency:** runCount=5 summary comparisons; if hosting blocked, keep Remote library and treat live invoke as CG-1 blocker — do not ship an unauthenticated workaround.

**Out of scope for CG-1:** calibration, final UI, Marketplace.

CG-2 implementation: `docs/codegeist/sprints/CG-02.md`, snapshot `os.1.0.0`, ADR-025.

CG-3 implementation: `docs/codegeist/sprints/CG-03.md`, ADR-026, `docs/calibration/`. Offline engine on `feat/codegeist-cg3-model-calibration`. Live operational calibration is not claimed.

CG-4 implementation: `docs/codegeist/sprints/CG-04.md`, ADR-027, `apps/simulation-api/app/interventions/`. Adapters over existing comparison. Live operational calibration is still not claimed.

CG-5 implementation: `docs/codegeist/sprints/CG-05.md`, ADR-028. Native multi-scenario lab. Live operational calibration is still not claimed.

CG-6 implementation: `docs/codegeist/sprints/CG-06.md`, ADR-029. Decision overlay on existing economics. Live operational calibration is still not claimed.
