# Repeated-Run Specification

## Purpose

Describe one operational model across multiple deterministic stochastic futures with bounded memory and explicit statistical/failure semantics.

## When to use

Use repeated execution to estimate a distribution of outcomes for one unchanged model and observation configuration. Do not use it for scenario comparison, causal claims, optimization, or recommendations.

## Inputs

Contract `0.4.0` accepts operational model `0.2.0`, base seed `0..2^63-1`, run count `2..500` (default 100), confidence level `0.90|0.95|0.99`, minimum successful ratio `0.5..1.0`, observation settings, optional explicit thresholds, and representative detail `summary|sampled|full`.

## Seed schedule

Run index is zero-based. `seed_i` is the unsigned big-endian integer represented by the first eight bytes of SHA-256 over UTF-8 `"<baseSeed>:<runIndex>"`. Algorithm metadata is `sha256_first_64_bits`. The schedule is platform-stable, prefix-stable, and independent of simulation RNG state.

## Run execution

Runs execute sequentially. Every ordinary run uses the exact single-run engine with the derived seed, shared observation configuration, and summary detail. Integrity validation occurs inside that run. No thread, process, async pool, worker, database, or writable persistence participates.

## Metric snapshots

Each successful run becomes a typed scalar snapshot. System fields are waiting, processing, cycle, p95, SLA, completion/failure rates, flow efficiency, time-weighted WIP/queue, rework, completions, failures, and event count. Stage fields are waiting, processing, time-weighted queue, failure rate, rework, and visits. Resource fields are utilization, idle proportion, request wait, maximum usage, and requests. Snapshots contain no events or item lifecycles.

## Aggregation

Each scalar uses Welford count/mean/sample variance, standard deviation, exact minimum/maximum, and a bounded scalar series for quantiles. Every aggregate count equals successful runs. Because one model is used, missing stage/resource identifiers are an integrity failure.

## Quantiles

Between-run p10/p50/p90 use nearest rank on sorted scalar values: index `ceil(p*n)-1`. They are outcome-distribution percentiles, not confidence bounds.

## Confidence intervals

Mean intervals use `mean ± z * s/sqrt(n)` with z `1.644854`, `1.959964`, or `2.575829`. Method is `normal_approximation`. Fewer than 30 successful samples are calculated but marked unreliable for sample size.

## Threshold risks

Only minimum SLA attainment and maximum average cycle, p95 cycle, time-weighted queue, and terminal failure rate are supported. Each configured result reports operator, threshold, exact violating count, successful valid denominator, and probability. Omitted thresholds return nothing.

## Failed-run handling

Failures retain run index, seed, safe category, and short safe message. Failed runs continue the batch but never affect aggregates or risks. A batch below its minimum successful ratio raises a structured error rather than returning an ordinary aggregate.

## Convergence diagnostics

At requested-run checkpoints 10, 25, 50, 100, 250, 500, plus the final count, report successful count and running means for SLA, average/p95 cycle, WIP, and queue, with change and relative change from the previous checkpoint. The label is `observed_running_mean_stability`; no automatic convergence conclusion is emitted.

## Representative run

Select the successful snapshot nearest the median vector of SLA, average cycle, p95 cycle, WIP, and rework after min/max normalization. Zero-range dimensions contribute zero; ties choose the lowest run index. Rerun only that seed using configured detail and require exact snapshot equality.

## Outputs

Return schema/model identity, requested/successful/failed counts and ratio, seed schedule/list, observation/confidence, system/stage/resource aggregates, configured risks, diagnostics, failures, representative metadata/result, deterministic execution metadata, and aggregate integrity status.

## Failure modes

Request validation rejects unsupported bounds or combinations. Per-run categories are `domain_validation`, `integrity_failure`, `execution_failure`, and `serialization_failure`. Batch ratio failure is safe and structured in API/CLI transports.

## Performance constraints

Run count is capped at 500. Ordinary events are not retained, full results are released each iteration, scalar series are bounded by metric count × 500, only one representative result is returned, execution is sequential, and no hosting limit is claimed without deployment evidence.
