# ADR-021: Playback is representative evidence

- Status: Proposed
- Date: 2026-07-18

## Context

Repeated-run and scenario-comparison conclusions come from aggregates over many summary runs (ADR-010, ADR-012). One retained representative run (`RepresentativeRunResult`, selected by normalized-median-vector distance) already carries ordered sampled events for a bounded set of items. Playback is useful for explaining temporal behavior — when queues formed, how resources were used, where rework occurred — but one run cannot represent the full stochastic distribution, and the product must not let a compelling animation read as aggregate certainty.

## Options considered

### Option A — Animate an aggregate/synthetic timeline

Would look smoother and "typical," but has no single source event log; any aggregate timeline would be fabricated, not simulation evidence.

### Option B — Stream the full event log of every run for playback

Maximizes fidelity but reintroduces unbounded event retention that ADR-010 deliberately removed, and requires a second execution mode.

### Option C — Reuse the existing retained representative run only, with mandatory representative-evidence labeling

Bounded, reproducible, and reuses evidence the product already returns for baseline and (when eligible) the top-ranked scenario.

## Decision

Choose Option C. Playback explains one retained representative sampled run (baseline or the selected scenario's own representative) and is never presented as aggregate evidence.

## Consequences

- Every playback view displays run index, seed, and selection method (`normalized_median_vector`) from `RepresentativeRunResult`.
- Every playback view displays the fixed disclaimer: "This playback illustrates one representative sampled run. Aggregate metrics, probabilities, and confidence intervals are calculated across all successful runs."
- Aggregate metrics, confidence intervals, and improvement probabilities remain visible in a separate aggregate-evidence panel and are never placed on the playback timeline.
- Playback language avoids "typical" unless the exact documented selection-method term is used in a technically justified context.
- Playback does not change ranking, confidence, risk, guardrail, or sensitivity results; it is a read-only presentation layer over evidence the backend already returns.
- Baseline and scenario representatives are independently selected (each by its own median-vector distance); playback discloses whether they happen to share a paired run index/seed or are separately selected, and never claims event-level pairing.

## Revisit triggers

- A product requirement emerges for full-event browsing beyond the retained representative.
- Multiple representative runs per variant are retained (ADR-010 revisit trigger).
- Users need cross-run animated aggregate visualization (would require new aggregate evidence design, not covered here).

Mark accepted after implementation and the Sprint 10 tests pass.
