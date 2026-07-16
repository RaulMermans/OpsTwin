# Sprint 08.1 — Sensitivity Contract and Evidence Polish

## Outcome

Bring every sensitivity surface into exact 0.6.0 parity: JSON Schema, Pydantic, API, CLI, canonical examples, benchmark validation, TypeScript adapters, exports, and UI evidence. This sprint adds no new analytical capability.

## Acceptance criteria

- Every published request and result field has a strict schema and matching runtime type.
- Unknown fields and non-finite numbers fail before execution or serialization.
- API responses, CLI stdout, examples, canonical replay, and benchmark-produced analytical results validate directly against the schemas.
- Boundary evidence covers zero baselines, signed domains, integer-only targets, probabilities 0/1, positive durations, capacity minima, duplicates, baseline location/cardinality, failed adjacency, two-success curves, and all-nonbaseline failure.
- Existing seed, pairing, work-budget, summary-retention, finite-difference, monotonicity, crossing, and elasticity semantics remain unchanged.

## Local gate

Targeted sensitivity contract, model, materializer, coordinator, API, CLI, benchmark, adapter, export, and UI tests must be source-green before Sprint 09 implementation proceeds. Environment failures are reported separately and never bypassed.

