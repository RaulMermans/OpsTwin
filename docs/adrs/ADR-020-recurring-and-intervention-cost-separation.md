# ADR-020 — Recurring and intervention cost separation

**Status:** Accepted

## Context

Recurring operating evidence describes one measurement period. A one-time intervention amount has a different time basis and cannot be added without an explicit allocation horizon.

## Decision

Return one-time intervention cost separately from recurring operating cost. Only a supplied positive integer `amortizationPeriods` permits division into an amortized cost per period and a combined per-period amount. Never infer the period count. Economic guardrails remain separate from operational guardrails and do not change the established operational ranking unless a request explicitly asks for a combined eligibility field.

## Consequences

The result avoids silent time-horizon mixing while still exposing transparent per-period evidence when the user supplies the missing assumption. No multi-period cash flow, payback, finance forecast, or prescriptive intervention claim is introduced.

