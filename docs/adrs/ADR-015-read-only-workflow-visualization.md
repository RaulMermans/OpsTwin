# ADR-015: Read-only workflow visualization

- Status: Proposed
- Date: 2026-07-16

## Context

Users need workflow structure before interpreting metrics. The operational model already contains stable entity IDs and relationships. Topology editing would require substantially broader validation and product design, while a general graph library would add unnecessary scope for one controlled template.

## Options considered

### Option A — Full editable graph

Adds creation, movement, and topology editing but requires a new validation and persistence product surface.

### Option B — External graph library in read-only mode

Provides layout and interaction utilities but adds dependency weight and abstractions not required by the canonical model.

### Option C — Small deterministic internal visualization layer

Maps existing IDs into a typed presentation model, controlled layout, semantic HTML, CSS Grid, and a small decorative SVG layer.

## Decision

Choose Option C. Sprint 07 will visualize the operational model through a read-only deterministic presentation layer rather than introducing a graph editor or changing the operational-model contract.

## Consequences

- Stable model IDs map to visual entities and layout is deterministic.
- There is no drag-and-drop or topology modification.
- The operational-model contract remains unchanged.
- Accessibility requires a complete textual equivalent.
- The canonical support template may use explicit frontend-only presentation metadata.

## Revisit triggers

- Users need topology editing.
- Multiple templates require automatic layout.
- Graph complexity exceeds controlled layout.
- A maintained diagram library provides clear net value.

This ADR remains Proposed until source implementation and required tests execute successfully.
