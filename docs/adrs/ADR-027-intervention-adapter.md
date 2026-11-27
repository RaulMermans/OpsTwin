# ADR-027: AI transformation interventions are adapters, not a second engine

- Status: accepted
- Date: 2026-11-27

## Context

CG-4 must let operators compare human and AI operating models inside Jira. The product already has an immutable baseline, an override registry, a scenario comparison coordinator, and CG-3 calibration artifacts. A second simulator, an LLM agent loop, or extra workers would duplicate mathematics and hide approximation class.

Calibrated canonical models use `itemCount=1` as a structural placeholder. Executing that volume would produce a one-item comparison that is not the experiment the UI describes.

## Decision

1. **Layer.** Platform-independent intervention translation lives in `apps/simulation-api/app/interventions/`. It emits existing `0.5.0` comparison requests. It does not import Forge modules.
2. **Catalog.** Supported kinds are capacity expansion, AI-assisted effective-mean processing, and hybrid route-probability auto-complete. Topology is not extended.
3. **Identities.** Model fingerprint stays independent of experiment `itemCount`, seed, and replication count. Execution volume must be at least 20. Placeholder `itemCount=1` is refused.
4. **Eligibility.** Missing or structurally invalid constructed models are refused. Valid constructed, assumption-based, historically failed, and historically adequate baselines may run when a model exists, with explicit class and disclosure.
5. **Remote.** `POST /api/integrations/atlassian/v1/transform` is FIT-authenticated and synthetic-fixture-only, like calibrate. Live snapshots and baseline models are not accepted from the client.

## Consequences

- Jira Experiments reuse Core comparison metrics and integrity.
- Effective-mean AI assistance does not reproduce mixture tails.
- Hybrid automation is unavailable when the calibrated route has no completion option.
- Live Jira operational calibration remains unclaimed.

## Validation

Focused adapter tests execute real calibration plus comparison. Remote tests cover FIT rejection and non-synthetic refusal. Forge Custom UI sends fixture identifiers and experiment execution, not models.
