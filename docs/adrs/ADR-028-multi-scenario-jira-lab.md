# ADR-028: Multi-scenario Jira experiments reuse one comparison

- Status: accepted
- Date: 2026-11-27

## Context

CG-4 executed one intervention per remote call. The product needs a common-baseline comparison of human, AI-assisted, and hybrid alternatives without a second engine. Golden synthetic routing has no triage completion option, so hybrid auto-complete was structurally refused.

## Decision

1. `run_multi_intervention_experiment` emits one `0.5.0` comparison with up to three catalog alternatives. Baseline runs once per experiment.
2. `cg5-hybrid-support` is a predeclared synthetic history with an empirical triage→completion share. Construction reuses existing routing options. Topology is not invented at intervention time.
3. `POST /api/integrations/atlassian/v1/transform` accepts `cg4.v1` (single intervention) or `cg5.v1` (alternatives). Fixture identifiers only.
4. Forge validates contract, identities, finite metrics, probability domain, and request/experiment identity before rendering.

## Consequences

- Hybrid remains disabled on golden routing.
- Partial experiments report failed alternatives without fabricating metrics.
- Interactive work stays inside the existing comparison work budget.
