# Scenario Comparison Specification

## Purpose

Measure how controlled operational parameter changes compare with a baseline across paired deterministic stochastic futures.

## When to use

Use comparison for one to five explicit parameter scenarios. Results are simulation evidence and comparative ranking, not causal proof, optimization, or operational recommendations.

## Inputs

Contract `0.5.0` contains a baseline `0.2.0` model, scenarios, execution settings, one objective, optional guardrails and repeated-risk thresholds, and representative-evidence settings.

## Baseline model

The baseline is validated once, hashed canonically, executed once per run index, and never mutated or re-executed separately per scenario.

## Scenario definitions

Scenario IDs are unique; names are nonempty; count is 1–5. Each scenario has 1–20 ordered overrides and optional description.

## Override targets and allowed fields

Only `replace` is supported:

- `resourcePool`: `capacity`.
- `source`: `arrivalInterval` for fixed arrivals or `meanInterarrivalTime` for Poisson arrivals.
- `stage`: `processing.fixed.value`, `processing.exponential.mean`, `processing.uniform.minimum`, `processing.uniform.maximum`, `processing.triangular.minimum`, `processing.triangular.mode`, `processing.triangular.maximum`, `failure.probability`, `maximumReworkAttempts`.
- `route`: `probability` for a route option identified by stable route ID and target entity ID encoded as the override entity ID `<routeId>:<targetId>`.
- `slaRule`: `targetDuration`.

IDs, names, types, item counts, references, destinations, topology, policies, and schema versions cannot change.

## Materialization

Deep-copy the baseline JSON, resolve every target through the centralized registry, reject duplicate targets, apply in request order, validate the complete model, verify topology identity, and parse a new independent typed model. Return exact applied summaries and SHA-256 of canonical alias-based JSON for baseline and scenario.

## Validation

Wrong operation, entity, ID, field, value type/range, distribution combination, route probability sum, or topology is rejected safely. One invalid scenario does not invalidate unrelated scenarios.

## Common random numbers

Baseline and all scenarios use the same child seed at index `i`, derived by the `0.4.0` SHA-256 schedule. Shared seeds reduce comparison noise where draw ordering remains comparable but do not guarantee event alignment after routing or draw-count changes.

## Paired execution

For each index, execute baseline once and then each valid scenario sequentially. All ordinary variants use the same observation settings and summary detail. Each successful result becomes a scalar snapshot and is released. No threads, processes, workers, persistence, or filesystem state participate.

## Variant aggregates

Baseline and each scenario reuse repeated-run system, stage, resource, risk, and confidence-interval aggregation. Failed runs are explicit and excluded.

## Paired deltas

For successful-index intersections, `delta = scenario - baseline`. Aggregate count, Welford mean/sample variance/standard deviation, min/max, nearest-rank p10/p50/p90, and normal-approximation mean interval. Relative delta is `delta / abs(baseline)`; a zero baseline yields null and increments `relativeDeltaUndefinedCount`.

## Metric directions

Higher is better: SLA attainment, completion rate, flow efficiency. Lower is better: waiting, average/p95 cycle, terminal failure, WIP, queue, and rework. Utilization is contextual, reported factually, allowed only as a maximum guardrail, and never an objective. Tolerance is centralized at `1e-9`.

## Risk comparisons

Configured repeated thresholds yield baseline/scenario risks, absolute probability-point change, nullable relative change, and paired baseline-only/scenario-only/both/neither violation counts. Language is observed paired simulation risk difference, not causal risk reduction.

## Objectives

Exactly one objective selects an objective-eligible metric and its registry-defined `maximize` or `minimize` direction. Contradictory direction is invalid.

## Guardrails

Supported operators are `lessThanOrEqual` and `greaterThanOrEqual` as authorized per metric. Sprint 04 evaluates scenario aggregate means only. Resource utilization guardrails name a resource pool and support maximum only.

## Comparative ranking

Eligible scenarios have valid models, adequate successful and paired ratios, and all guardrails passed. Ranking uses directed paired mean delta, improvement probability, narrower interval, then scenario ID. Every row exposes eligibility, guardrails, calculation, and tie-break explanation.

## Representative evidence

By default rerun the baseline median-vector representative and the top-ranked eligible scenario's own median-vector representative using their original seeds. Detail is sampled with limit 25 by default. Snapshot equality is mandatory. At most two event-rich results are retained; if no scenario is eligible, only baseline is returned.

## Failure handling

Safe scenario categories are `override_validation`, `materialization_validation`, `domain_validation`, `paired_execution`, `paired_ratio_failure`, and `serialization_failure`. Baseline validation/execution or request work-budget failure invalidates the request. Failed scenarios remain visible and are excluded from paired statistics/ranking.

## Work limits

Scenario count is 1–5, overrides 1–20 per scenario, run count 2–500, ratios 0.5–1.0, representative limit 1–1000, and estimated work at most 100,000 item executions. Work metadata reports variants, runs, baseline items, estimated/maximum units, and estimated total item executions before execution.

## Outputs

Return hashes/materialization metadata, execution/seeds, baseline and scenario variant evidence, paired distributions, improvement/risk results, guardrails, comparative ranking, factual statements, safe failures, representative results, work budget, and real comparison integrity.

## Failure modes

Request validation uses HTTP 422/CLI parse failure. Work or baseline failure is a safe comparison error. Scenario-level failures may coexist with a valid baseline and other valid scenarios. No raw exception text is returned.
