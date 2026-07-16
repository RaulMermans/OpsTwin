# ADR-006: Operational model schema evolution

- Status: accepted

## Context

Version `0.1.0` supports one source and one process stage. Sprint 01 requires collections of sources, stages, resources, and routes. No production users or persisted external models exist, so runtime compatibility branches would add complexity without protecting real data.

## Options considered

### Option A — Replace the schema cleanly

Adopt `0.2.0` as the only accepted runtime model and retain prior behavior through an equivalent fixture.

### Option B — Support both `0.1.0` and `0.2.0`

Maintain parallel validation and execution paths.

### Option C — Create a migration utility and retain both formats

Add conversion tooling plus both runtime formats before persistence exists.

## Decision

Replace the Sprint 00 operational model contract with schema version `0.2.0` rather than maintaining runtime backward compatibility before public persistence exists.

## Rationale

A clean replacement keeps the kernel and contracts small while exact `0.2.0` regression tests preserve the validated mathematics.

## Consequences

- Existing examples move to `0.2.0`.
- A `0.2.0` equivalent fixture preserves Sprint 00 deterministic behavior.
- Unsupported schema versions are rejected.
- Compatibility must be revisited once models are persisted or externally shared.

## Revisit triggers

- Public models are saved.
- Database persistence is introduced.
- External integrations depend on stable schema versions.
- Users need model import/export across versions.

## Validation plan

Test rejection of `0.1.0`, schema conformance of every example, and exact Sprint 00-equivalent lifecycle metrics under `0.2.0`.
