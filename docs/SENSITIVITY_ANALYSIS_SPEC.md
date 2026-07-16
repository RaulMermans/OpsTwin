# Sensitivity Analysis Specification

## When to use

Use sensitivity analysis to describe how one selected model assumption and one or more observed outputs relate across an explicit tested range. It does not establish causality, find an optimum, or measure interactions.

## Inputs and target

The request uses schema `0.6.0`, one `0.2.0` baseline model, one identity-based target, 2–10 finite distinct numeric values, bounded execution, 1–8 metrics, and optional existing risk thresholds. The sensitivity metadata layer delegates every mutation to the scenario override registry; it adds only labels, units, and integer/number metadata.

Supported targets are resource-pool `capacity`; source `arrivalInterval` and `meanInterarrivalTime`; fixed, exponential, uniform, and triangular processing scalars; stage `failure.probability` and `maximumReworkAttempts`; route-option `probability` using `routeId:targetId`; and SLA `targetDuration`.

## Baseline and value semantics

The original order is retained as metadata. Execution and curves use ascending canonical numeric order. Duplicate values are rejected. The actual baseline scalar must be explicitly present; it is never injected. Integer targets reject fractional values. The baseline object is not mutated, and every non-baseline variant passes full operational-model validation.

Route siblings are never renormalized. Therefore a changed probability that makes the route sum invalid is rejected as domain validation evidence.

## Pairing and retention

For run index `i`, derive `seed_i = first64bits(SHA-256(baseSeed + ":" + i))`. Execute the canonical values sequentially under that shared seed, with the baseline value once. Ordinary executions use summary detail and retain scalar snapshots only. Failed non-baseline value runs are isolated; baseline failure invalidates the analysis.

Work units are `baseline item count × run count × tested value count` and must not exceed 100,000.

## Aggregation and paired deltas

Selected metric aggregates use the existing online aggregate structure and confidence levels. For every valid non-baseline value and paired index, `delta_i = tested_i - baseline_i`; relative deltas, confidence evidence, and improvement/tie classification reuse comparison formulas and metric-direction metadata.

## Response analysis

Points remain discrete and canonically ordered. Failed points remain present with null evidence. No interpolation or extrapolation is performed.

An adjacent finite difference is `(metric_b - metric_a) / (parameter_b - parameter_a)` and is emitted only when both adjacent tested points succeed.

Observed elasticity is `((metric - baselineMetric) / abs(baselineMetric)) / ((parameter - baselineParameter) / abs(baselineParameter))`. It is null for the baseline point, zero baseline parameter, zero baseline metric, zero percentage parameter change, or non-finite input; infinity is never serialized.

Monotonicity labels are `observed_increasing`, `observed_decreasing`, `observed_flat`, `observed_mixed`, and `insufficient_evidence`, using the shared `1e-9` comparison tolerance. Labels describe only successful tested values.

Threshold crossings compare only adjacent successful points. The result states the lower and upper tested values, observed metrics, compliance direction, and label `Observed threshold crossing interval`; it never estimates an exact crossing.

## Failures, validation, and outputs

Public categories are `target_validation`, `value_validation`, `materialization_validation`, `domain_validation`, `execution_failure`, `integrity_failure`, `paired_ratio_failure`, and `serialization_failure`. The endpoint is `POST /api/simulation/analyze/sensitivity`; the CLI is `python -m app.cli sensitivity <request-path>`. Both return the typed `0.6.0` result or a safe structured/non-zero failure. The result includes hashes, target metadata, value order, seeds, budget, per-value evidence, curves, execution retention, and an actual integrity-check count.

## Deferred capabilities

Multiple targets, interaction effects, automated value generation, recommendations, optimization, costs, persistence, background execution, and interpolated curves remain deferred.
