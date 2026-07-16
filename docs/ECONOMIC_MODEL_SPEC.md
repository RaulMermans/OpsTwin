# Economic Model Specification

## Contract

Economic assumptions use schema version `0.7.0`, one uppercase ISO-style three-letter currency code, and the operational model's time unit. At least one category is configured. All rates and fixed amounts are finite and greater than or equal to zero. Entity-scoped assumptions resolve to unique known stage or resource IDs.

## Recurring categories

| Category | Quantity | Formula |
| --- | --- | --- |
| Resource provisioning | configured capacity and measurement duration | `capacity × duration × rate` |
| Stage visits | measured visit count | `visits × rate` |
| Queue holding | time-weighted queue and duration | `TW queue × duration × rate` |
| WIP holding | time-weighted WIP and duration | `TW WIP × duration × rate` |
| SLA violations | included items not attaining SLA | `violations × rate` |
| Terminal failure | terminal failure count | `failures × rate` |
| Rework | global or stage rework count | `rework × rate` |
| Completion | completed item count | `completed × rate` |
| Fixed period | one configured amount | added once |

Measurement duration excludes warmup. Resource provisioning uses capacity, never utilization. Cost per completed item is recurring operating cost divided by completed count and is null at zero completions.

## Evidence states

A configured component is `available` only when all required source evidence exists. A configured missing source is `unavailable` and makes the recurring total unavailable. An unconfigured category is `not_configured` and contributes zero. Zero is evidence only when a category was explicitly configured with a zero rate.

## Evaluation boundary

The evaluator is a pure function of one successful summary simulation result, its materialized model, observation duration, and validated assumptions. It returns scalar operands, safe formula labels, component status, coverage, missing components, recurring total, completion count, cost per completion, currency, and integrity evidence. It retains no events.

