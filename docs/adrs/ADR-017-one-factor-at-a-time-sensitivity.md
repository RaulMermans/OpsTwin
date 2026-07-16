# ADR-017 — One-factor-at-a-time sensitivity

**Status:** Accepted

## Context

Users need to inspect which explicit assumptions influence observed outputs. Multi-dimensional sweeps multiply work and make attribution ambiguous, while existing identity-based overrides already express bounded scalar changes.

## Options considered

1. One-factor-at-a-time explicit sweeps.
2. Multi-factor grid search.
3. Optimization with generated candidates.

## Decision

Adopt option 1. Each `0.6.0` request contains one registered target and explicit values including the baseline. Execution uses paired common-random-number seeds and describes only the tested range.

## Consequences

The result is reproducible and interpretable, but cannot estimate interactions or claim an optimum. Invalid route sums fail without sibling renormalization. The 100,000-unit synchronous budget remains authoritative. Acceptance followed passing focused model, materialization, analytics, coordinator, API, CLI, and benchmark tests.
