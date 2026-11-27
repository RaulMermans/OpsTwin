# ADR-026: Platform-independent calibration stays outside Core topology

- Status: accepted
- Date: 2026-11-27

## Context

CG-3 must turn validated operational snapshots into inspectable simulation models without treating Jira status residence as service time, without sending live snapshots to the existing FIT compare endpoint, and without teaching OpsTwin Core about Jira.

The engine already supports Poisson or fixed arrivals, exponential/fixed/uniform/triangular processing, FIFO or priority queues, finite `itemCount`, optional stage failure/rework, and identity-locked scenario topology. It does not support gamma, lognormal, empirical, or time-varying arrivals, business calendars, or arbitrary workflow discovery.

## Decision

1. **Layer.** Calibration lives in `apps/simulation-api/app/calibration/`. It reads `os.1.0.0` snapshots and emits Core `0.2.0` models. It does not import Forge modules.
2. **Template.** CG-3 supports one model class: `support-triage-resolution.1` (queue → triage → resolution → completion). Observed workflows that need additional processing stages or review loops return `unsupported_topology`.
3. **Identifiability before numbers.** Arrival rate may be estimated from training-window created timestamps. Active processing time is not estimated from status residence. Capacity is not estimated from assignee counts. Rework is not estimated from reopening. Missing material parameters require explicitly approved assumptions.
4. **Holdout.** Parameters are fit on an earlier training window only. Validation is **generative** (the engine samples arrivals) against a later holdout. Replay of historical arrivals is not implemented and must not be described as arrival-process validation.
5. **Remote.** `POST /api/integrations/atlassian/v1/compare` remains synthetic-catalog-only. A separate `POST /api/integrations/atlassian/v1/calibrate` accepts fixture identifiers only (Option A). Live operational-data egress is out of scope until independent project and user authorization for that purpose is verified.
6. **Uncertainty.** Poisson-rate intervals are statistical. Assumption ranges are labeled separately. They are never merged into a confidence percentage.

## Consequences

- Offline calibration can pass without live Jira history.
- Native Jira UX may demonstrate synthetic calibration only.
- Historical validation never implies causal validity of future AI interventions.
- Synthetic recovery is consistency within the laboratory generator, not real-world accuracy.
