# ADR-018 — Paired sensitivity execution

**Status:** Accepted

## Context

One-factor-at-a-time sensitivity must distinguish observed parameter response from independent Monte Carlo noise. Values also need comparable failure and confidence evidence without multiplying retained data.

## Decision

Execute sensitivity in run-index-first order. For every run index, derive one deterministic seed with the established SHA-256 schedule and use that seed for the baseline value and every materialized non-baseline value. Pair evidence by the intersection of successful run indexes. The tested values are canonicalized for execution while the original request order remains evidence. Ordinary executions use summary detail and retain zero events.

The explicit baseline parameter value must appear exactly once after uniqueness validation. A baseline execution failure invalidates the analysis; non-baseline failures remain isolated and are governed by successful-run and paired-run ratios. Work units remain `baseline item count × run count × tested value count` under the existing synchronous limit.

## Consequences

Paired deltas and probabilities use common random numbers, deterministic replay is possible from the published seed schedule, and failed values cannot silently contaminate adjacent response evidence. This decision adds no interpolation, causal claim, optimization, recommendation, persistence, or additional simulation work.
