# ADR-012: Paired common random numbers

- Status: accepted

## Context

Independent schedules add avoidable comparison noise. Corresponding variants should share comparable inputs, and paired differences are stronger evidence than subtracting independent aggregate means. Structural/draw changes can still diverge streams.

## Options considered

### Option A — Independent seed schedules

Simple but needlessly increases variance.

### Option B — Shared seed schedule with paired run indexes

Reuses the accepted deterministic schedule and supports direct paired differences.

### Option C — Persist complete exogenous random streams

Stronger alignment but requires new modelling and persistence semantics.

## Decision

Choose Option B. Baseline and every scenario at index `i` use the same derived child seed.

## Consequences

Paired deltas use only jointly successful indexes. Same requests replay exactly. Shared seeds reduce noise where draw structure remains comparable but do not guarantee event-level alignment after routing or draw-count changes.

## Revisit triggers

Structural changes, stronger variance reduction, separated exogenous demand streams, or distributed pairing manifests.

## Validation plan

Exact paired seeds, same-request reproducibility, controlled paired deltas, intersection/failure checks, and documented draw-divergence limitation.
