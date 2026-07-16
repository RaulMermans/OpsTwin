# ADR-003: Event log as canonical simulation output

- Status: accepted

## Context

Metrics alone cannot explain scheduling, reproduce calculations, or support later playback.

## Decision

Derive metrics, debugging evidence, and future animation from a normalized simulation event stream.

## Options considered

Event stream; aggregate metrics only; mutable item snapshots; engine-specific traces.

## Rationale

Stable events preserve causal evidence and allow independent metric checks without coupling consumers to SimPy internals.

## Consequences

Event semantics and order are public behavior. Results are larger, and schema evolution must be deliberate.

## Revisit triggers

Event volume becomes prohibitive or a validated use case requires state not reconstructable from events.

## Validation plan

Assert exact event types, timestamps, sequence order, count, and repeatability in golden-model tests.
