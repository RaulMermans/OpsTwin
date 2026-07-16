# ADR-011: Identity-based scenario overrides

- Status: accepted

## Context

Scenarios should expose intentional changes. Full model copies drift, numerical array indexes are fragile, arbitrary JSON Patch expands validation complexity, and stable operational entity IDs already exist.

## Options considered

### Option A — Complete model copy per scenario

Portable but duplicates unchanged structure and obscures changes.

### Option B — Generic JSON Patch

Compact but admits fragile indexes and unrestricted structural edits.

### Option C — Domain-specific identity-based replacements

Explicit, deterministic, auditable, and compatible with domain validation.

## Decision

Choose Option C. Overrides identify entity type, stable entity ID, approved field, `replace`, and typed scalar value.

## Consequences

Only registry-approved fields change; materialization is deterministic; applied changes are reported; topology changes, add/remove/move/copy, and unrestricted paths remain deferred.

## Revisit triggers

Users need entity addition/removal, structural routes, scenario templates with topology edits, or a versioned model-editing language.

## Validation plan

Exact override fixture, baseline immutability, scenario isolation, unknown-entity/field rejection, wrong-type/range rejection, duplicate-target rejection, and full-model revalidation.
