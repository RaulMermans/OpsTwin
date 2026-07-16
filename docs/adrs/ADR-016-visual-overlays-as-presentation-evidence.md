# ADR-016: Visual overlays are presentation evidence

- Status: Accepted
- Date: 2026-07-16

## Context

Users benefit from seeing observed operational pressure on the workflow. The backend already returns stage and resource metrics. Creating a frontend operational score would introduce a second analytical source of truth, while visual intensity can communicate relative display range without adding a business conclusion.

## Decision

Workflow overlays visualize backend-returned metrics and explicit scenario overrides without introducing new operational scores, recommendations, or simulation calculations.

- Use backend metrics directly and retain the raw value.
- Use documented min/max display scaling across visible finite values.
- Label the scaling as relative within the current result.
- Do not generate advisory language.
- Do not classify an entity as a confirmed constraint unless backend evidence explicitly supplies that classification.

Preferred terms include “Operational pressure”, “Observed queue”, “Observed waiting”, “Observed utilization”, and “Observed failure/rework”.

## Consequences

Overlay intensity is presentation-only, unavailable evidence remains unavailable, equal values receive neutral intensity, and no scaling result affects ranking, scenario status, guardrails, or requests.
