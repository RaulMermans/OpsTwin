# Sprint 04 — Scenario Overrides and Paired Comparison

## Objective

Compare one validated baseline with one to five controlled numeric scenarios across the same deterministic stochastic futures. Return variant distributions, paired differences, risk evidence, guardrail eligibility, and an explicit comparative ranking without recommendations.

## Current baseline

Sprint 03.1 provides operational model `0.2.0`, single-run `0.3.0`, repeated-run `0.4.0`, compact emission-time auditing, sequential repeated execution, deterministic SHA-256 child seeds, scalar snapshots, normal-approximation intervals, safe failures, and bounded representative evidence.

## In scope

- Separate scenario comparison request/result contract `0.5.0`.
- Identity-based `replace` overrides against stable source, stage, route, resource-pool, and SLA-rule IDs.
- Immutable materialization, complete domain revalidation, topology verification, applied-override audit, and canonical hashes.
- Shared child seed by run index, sequential baseline-once-plus-scenarios execution, and summary-only ordinary evidence.
- Independent variant aggregates and successful-index paired absolute/relative delta distributions.
- Centralized metric direction, improvement probabilities, threshold-risk quadrants, explicit objective, mean guardrails, and deterministic comparative ranking.
- Baseline and top-ranked eligible scenario representative reruns only.
- Safe scenario failure isolation, comparison integrity, work budget, API, CLI, tests, and benchmark evidence.

## Out of scope

Persistence, scenario storage, topology edits, arbitrary JSON Patch, authentication, workflow editing, charts, animation, causal claims, recommendations, sensitivity sweeps, optimization, costs, parallelism, workers, deployment configuration, and LLM features.

## Scenario and override semantics

A scenario is an ordered, bounded set of unique replacement targets. The registry authorizes only documented numeric fields. Materialization deep-copies the baseline, resolves stable IDs, applies replacements in request order, validates the complete operational model, verifies topology identity, and returns deterministic canonical hashes. Invalid scenarios remain visible but do not affect valid scenarios.

## Paired-run semantics

For index `i`, baseline and every scenario use the existing `sha256_first_64_bits` seed. Execution order is baseline once, then scenarios in request order. Ordinary runs are summary-only and released after scalar snapshot extraction. Scenario paired statistics use only the intersection of successful baseline and scenario indexes; no aggregate-mean subtraction substitutes for missing pairs.

## Metric direction and delta formulas

Absolute delta is `scenario - baseline`. Relative delta is `delta / abs(baseline)` when baseline is nonzero; otherwise it is null and increments the undefined count. Higher-is-better metrics improve above tolerance; lower-is-better metrics improve below negative tolerance. Resource utilization is factual/contextual and cannot be a primary objective.

## Risk comparison

For every configured repeated-run threshold, return baseline/scenario violation probabilities, probability-point change, nullable relative change, and paired counts for baseline-only, scenario-only, both, and neither violating.

## Ranking semantics

Only materialized scenarios meeting successful/paired ratios and all mean guardrails are eligible. Sort by directed objective mean delta, improvement probability, narrower paired-delta interval, and scenario ID. Results are labelled comparative ranking and never recommendations.

## Failure handling

Scenario categories are `override_validation`, `materialization_validation`, `domain_validation`, `paired_execution`, `paired_ratio_failure`, and `serialization_failure`. Baseline failure invalidates the request. Scenario failures are safe, visible, isolated, and excluded from ranking and paired statistics.

## Performance budget

Estimated work is baseline item count × run count × model variants. Sprint 04 caps this at 100,000 item executions before simulation. This local synchronous engineering guard is supported by the existing 50,000-item repeated baseline and required 30,000-unit comparison matrix; it is not a hosting claim.

## Test plan

GM-030–GM-041 cover override application/rejection, immutability, paired seeds/deltas, improvement and zero-relative behavior, reproducibility, ranking, failure isolation, integrity, and performance. Tests follow red-green slices and reuse aggregation primitives.

## Acceptance criteria

All AC1–AC12 in the work package pass, actual request/result payloads validate, earlier contracts remain unchanged, ordinary events remain zero, paired intersections and rankings reconcile, representatives match, all commands pass, and scope remains bounded.

## Definition of done

Fresh bootstrap/verify, all regressions and golden models, all three full benchmarks, two identical canonical comparisons, schema/API/CLI checks, repository audits, documentation, and scratchpad are complete without commit or push.

## Rollback plan

Stop on a repeated-engine regression. Preserve registry/materializer tests, disable comparison transport, restore paired snapshots before aggregates, restore metrics before ranking, and keep representative evidence disabled until exact rerun matching is green. Never weaken retention, seed, integrity, or failure tests and never add parallelism as a workaround.
