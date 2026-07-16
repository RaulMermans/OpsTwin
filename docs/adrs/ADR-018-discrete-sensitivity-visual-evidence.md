# Superseded design note — Discrete sensitivity visual evidence

**Status:** Superseded by `ADR-018-paired-sensitivity-execution.md`

## Context

Sensitivity evidence needs a compact Scenario Lab presentation without implying continuous knowledge between tested values or introducing a chart dependency.

## Decision

Render an in-place HTML/CSS/SVG section. Straight segments connect adjacent successful points only; failed points break the line. Confidence intervals and the baseline are visibly marked, and a numeric table always accompanies the SVG.

## Consequences

The view is lightweight, accessible, and honest about discrete evidence. It does not interpolate, extrapolate, optimize, or recommend. More elaborate exploration remains deferred.

This presentation decision remains in force as a design note. The canonical ADR-018 identifier is assigned to the more foundational paired-execution decision expected by the Sprint 08 contract.
