# ADR-004: Scenarios as baseline overrides

- Status: accepted

## Context

Copying full models for every future scenario obscures the intervention and creates configuration drift.

## Decision

Future scenarios will store parameter overrides against a versioned baseline rather than duplicate complete operational models.

## Options considered

Baseline overrides; complete copies; event-sourced model edits; free-form scenario scripts.

## Rationale

Overrides make comparisons explicit, compact, and auditable while preserving a stable baseline.

## Consequences

Resolution and baseline versioning must be deterministic. Scenario execution is intentionally not implemented in Sprint 00.

## Revisit triggers

Structural changes cannot be expressed safely as overrides or users require independently portable full models.

## Validation plan

In the scenario sprint, test resolution, provenance, baseline version mismatch, and comparison labeling.
