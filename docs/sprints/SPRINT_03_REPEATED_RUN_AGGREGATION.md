# Sprint 03 — Repeated-Run Aggregation Core

## Objective

Execute one validated operational model across independently seeded stochastic futures and return statistically meaningful aggregates with one bounded representative rerun. This sprint describes model behavior across runs; it does not compare scenarios or recommend decisions.

## Current baseline

Sprint 02.1 provides stateless seed-reproducible single runs, explicit observation windows, exact time-weighted metrics, 16 compact-ledger integrity groups, and emission-time summary/sampled/full retention. Single-run contracts are operational model `0.2.0` and request/result `0.3.0`.

## In scope

- Separate repeated request/result contracts at `0.4.0`.
- Deterministic SHA-256 child-seed schedule for 2–500 sequential runs.
- Compact per-run scalar snapshots and numerically stable aggregation.
- Nearest-rank run quantiles and normal-approximation confidence intervals.
- Explicit system risk thresholds, safe failed-run evidence, and minimum success ratio.
- Running-mean stability checkpoints.
- Median-vector representative selection followed by one bounded rerun.
- Synchronous API, CLI, schemas, golden models, and local performance evidence.

## Out of scope

Scenario overrides/comparison, persistence, databases, authentication, workflow editing, charts, animation, recommendations, sensitivity analysis, background jobs, parallelism, distributed execution, deployment configuration, external integrations, and LLM features.

## Architecture impact

The single-run engine remains the sole simulation boundary. A repeated coordinator derives seeds, invokes ordinary runs in summary mode sequentially, extracts scalar snapshots, updates accumulators, and releases each result. After successful aggregation it selects and reruns one representative seed. No shared mutable request state or writable persistence is introduced.

## Repeated-run request semantics

The request contains the model, base seed, run count, confidence level, minimum successful-run ratio, single-run observation configuration, optional explicit thresholds, and representative detail. Defaults are run count 100, confidence 0.95, minimum ratio 1.0, and representative sampled detail. Run count is bounded to 2–500.

## Seed-schedule semantics

For zero-based index `i`, encode `"<baseSeed>:<i>"` as UTF-8, calculate SHA-256, and interpret the first eight digest bytes as an unsigned big-endian integer. The algorithm identifier is `sha256_first_64_bits`. Increasing run count preserves every earlier seed.

## Aggregation formulas

Welford updates count, mean, and second central moment `M2`; sample variance is `M2/(n-1)` for `n>1`, otherwise zero. Standard deviation is its square root. Minimum and maximum are exact. Scalar samples are retained per metric because the run cap is 500; complete run results are not.

## Quantile method

Run-distribution p10, p50, and p90 use nearest rank: sorted value at `ceil(p*n)-1`, clamped to the valid index. These percentiles describe between-run outcomes and are not confidence intervals.

## Confidence-interval method

Mean intervals use the documented normal approximation `mean ± z * sampleStandardDeviation/sqrt(n)` with z values `1.644854`, `1.959964`, and `2.575829` for 90%, 95%, and 99%. Results with fewer than 30 successful runs set `reliableSampleSize=false`; the interval is not described as exact for small samples.

## Failure policy

Failures are safely classified as `domain_validation`, `integrity_failure`, `execution_failure`, or `serialization_failure`. Execution continues, failed indexes/seeds are reported, and failed runs never enter aggregates or threshold denominators. If `successfulRuns/requestedRuns` is below the configured minimum, the coordinator raises a structured repeated-run failure.

## Representative-run method

For every successful snapshot, use SLA attainment, average cycle time, p95 cycle time, time-weighted WIP, and total rework count. Calculate the component median, normalize distances using observed min/max, treat zero-range dimensions as zero, and choose minimum Euclidean distance with lowest run index as tie-breaker. Rerun that seed once with configured detail and require an exact scalar-snapshot match.

## Result-retention policy

Ordinary runs use summary retention and only scalar snapshots survive their iteration. At most one single-run result is live at a time. The returned repeated result embeds only the representative single-run result; it never returns every run result or event history.

## Performance test plan

Measure 100 items × 10/100 runs and 1,000 items × 10/50 runs. Record wall time, mean ordinary-run time, total generated events, response and representative bytes, success/failure counts, returned events, maximum simultaneously retained single-run results, and integrity. Ordinary runs are summary; representative evidence is sampled and bounded.

## Acceptance criteria

All AC1–AC12 in the work package pass: retention hardening remains green; `0.4.0` contracts/docs/ADRs exist; seed prefix, aggregation, risks, failure accounting, representative rerun, diagnostics, performance evidence, quality gates, and scope control are executable and verified.

## Definition of done

GM-019 through GM-029, actual schema/API/CLI payloads, repeated reproducibility, seed-prefix stability, representative match, both benchmarks, `pnpm verify`, audits, documentation, and scratchpad are complete with no commit or push.

## Rollback plan

Stop repeated feature work on any single-run regression. Preserve compact retention, then isolate seed schedule, aggregation primitives, coordinator, and transports in that order. Keep accurate failing tests, never restore full ordinary event retention as a shortcut, and never introduce concurrency to mask cost.
