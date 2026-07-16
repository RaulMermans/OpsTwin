# ADR-007: Observation windows and time-weighted metrics

- Status: accepted

## Context

Queue length, WIP, and utilization change continuously through simulation time. Averaging values only at event timestamps can bias results, steady-state validation requires warm-up exclusion, and future comparison needs stable metric semantics.

## Options considered

### Option A — Event-snapshot averages

Average state values only when events occur. This overweights periods with dense events.

### Option B — Time-weighted integration over an explicit window

Integrate each step state over its duration, clipped to explicit measurement boundaries.

### Option C — Periodic sampling

Sample state on a clock. This introduces interval choice and approximation error.

## Decision

Operational state metrics will be measured over an explicit observation window using time-weighted integration rather than event-snapshot averages.

## Consequences

- Metric collectors track state changes and area under step functions.
- Warm-up and measurement windows are explicit.
- Pre-warm-up events establish boundary state but add no measured area.
- Item-level and system-state metrics use separate documented inclusion rules.
- Existing deterministic metrics remain compatible where definitions overlap.

## Revisit triggers

- Continuous-state simulation is introduced.
- Calendar-aware operating periods are added.
- Distributed simulation requires a different aggregation model.

## Validation plan

Use a hand-calculated deterministic queue-area fixture, an M/M/1 comparison, and Little's Law reconciliation.
