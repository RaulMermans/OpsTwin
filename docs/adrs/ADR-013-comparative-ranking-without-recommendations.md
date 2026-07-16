# ADR-013: Comparative ranking without recommendations

- Status: accepted

## Context

Users need clear comparisons. Deterministic ranking can use explicit objectives and guardrails, while recommendations require validated cost, constraint, and intervention semantics that do not exist.

## Decision

Allow deterministic comparative ranking from a user-selected objective and optional guardrails. Do not generate recommendations.

## Consequences

Invalid or guardrail-failing scenarios remain visible but unranked. Eligible rankings expose directed paired mean delta, improvement probability, confidence width, and deterministic ID tie-break. Output says comparative ranking, never recommended, best action, or optimal intervention.

## Revisit triggers

Validated cost models, intervention libraries, sensitivity analysis, or recommendation rules become available.

## Validation plan

Objective-direction validation, guardrail filtering, probability/interval/ID tie-break fixtures, failure exclusion, factual-language scan, and no recommendation terms.
