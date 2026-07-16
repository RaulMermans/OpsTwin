# ADR-009: Deterministic repeated-run seed schedule

- Status: accepted

## Context

Repeated runs require independent reproducible seeds. Increasing run count must preserve the previous prefix, child generation must not consume simulation RNG, and the schedule must be stable across platforms.

## Options considered

### Option A — Base seed plus run index

Simple but exposes avoidable correlation structure and weak separation.

### Option B — One RNG generates child seeds

Reproducible but couples the public schedule to RNG implementation and draw order.

### Option C — Stable hash of base seed and run index

Platform-stable, prefix-stable, and independent of simulation execution.

## Decision

Derive each seed from the first unsigned 64 bits of SHA-256 over UTF-8 `"<baseSeed>:<runIndex>"`, interpreted big-endian. The public identifier is `sha256_first_64_bits`.

## Consequences

Every run is traceable; prefixes remain stable; seed derivation is independent; and this algorithm becomes part of contract `0.4.0`.

## Revisit triggers

Cross-language reproduction reveals an encoding ambiguity, distributed index partitioning is introduced, or SHA-256 availability becomes constrained.

## Validation plan

Assert exact seeds for base 42, 50/100 prefix equality, uniqueness through 500 indexes, cross-process equality, and unchanged simulation RNG state.
