# Sprint 08 — Sensitivity Analysis Core

## Outcome

Sprint 08 adds bounded one-factor-at-a-time sensitivity analysis as a local, stateless `0.6.0` product slice. One registered scalar assumption is evaluated at 2–10 explicit values using common run-index seeds, sequential execution, summary-only evidence, existing aggregates, and existing paired-delta semantics.

## In scope

- Resource capacity, fixed/Poisson arrival, supported processing-distribution parameters, failure probability, rework attempts, route probability, and SLA duration targets.
- Two to ten distinct values, two to one hundred runs, and one to eight selected system metrics.
- Canonical numeric order, explicit baseline inclusion, immutable materialization, per-value aggregates, paired deltas, finite differences, observed elasticity, monotonicity, and adjacent threshold intervals.
- Typed request/result contracts, FastAPI endpoint, file-based CLI, compact Scenario Lab panel, integrity validation, golden-master coverage, and a local benchmark matrix.

## Out of scope

Multi-factor sweeps, interaction effects, grids, optimization, automatic values, cost functions, interpolated crossings, extrapolation, recommendations, persistence, asynchronous jobs, and deployment.

## Acceptance and definition of done

The slice is complete when the `0.6.0` contracts remain separate from `0.5.0`, all targets reuse the override registry, the baseline executes once per run index, all ordinary runs retain zero events, invalid route sums fail rather than renormalize, the 100,000-unit work limit is enforced before execution, at least 18 integrity checks reconcile, API/CLI/UI expose the same result, focused backend tests pass, and blocked frontend/build gates are reported without weakening or retrying them.

## Test plan

GM-081 through GM-099 cover targets, materialization, immutability, canonical ordering, seed pairing, baseline reuse, aggregates, paired deltas, finite differences, elasticity, monotonicity, thresholds, failure isolation, budget, replay, event retention, payload size, and language. Focused test modules mirror these boundaries.
