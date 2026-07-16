# ADR-019 — Explicit economic assumptions

**Status:** Accepted

## Context

Operational simulation results contain quantities, not monetary meaning. Inferring rates from utilization, labels, currency locale, or scenario type would create hidden business assumptions and make evidence irreproducible.

## Decision

Accept economics only through a strict `0.7.0` assumption contract. The request supplies one uppercase three-letter currency, the operational model time unit, and at least one finite non-negative rate or fixed amount. Entity-scoped assumptions resolve uniquely to known stage or resource IDs. Unconfigured categories are `not_configured`; configured missing evidence is `unavailable` and invalidates the recurring total.

Formulas live in one cost-source registry and a pure per-run evaluator. They use measurement-period quantities from the same summary result, never retained events or reconstructed aggregate distributions.

## Consequences

Every returned component is traceable to explicit operands, deterministic replay is possible, and zero can be distinguished from missing configuration. The system does not calculate revenue, profit, ROI, or an inferred economic optimum.

