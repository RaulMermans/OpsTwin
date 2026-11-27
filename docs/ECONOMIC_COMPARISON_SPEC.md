# Economic Comparison Specification

## Paired execution

Economics observes the same run index, seed, materialized variant, observation window, and successful summary result used by operational comparison. It does not rerun a scenario solely to calculate costs. Failed simulation runs never enter costs; failed cost evaluation is tracked separately; pairing uses the intersection of successful economic snapshots.

For each scenario, aggregate baseline and scenario recurring cost, component costs, and defined cost per completion. Return absolute and relative paired deltas, undefined relative count, lower/higher/tied probabilities, paired counts and ratios, and component deltas using the established tie convention with a documented monetary tolerance.

## Intervention costs

One-time intervention cost is separate from recurring cost. Only an explicitly supplied positive amortization period permits `oneTimeCost / amortizationPeriods` and a combined per-period value. The system never infers periods.

## Objective relationship

The selected objective comes from the existing metric registry and paired comparison evidence. Trade-off classifications are factual: lower/higher/flat cost crossed with improved/degraded/flat objective, otherwise `mixed_or_insufficient_evidence`. Economic guardrails are reported separately and do not change operational rank.

Incremental recurring cost per observed unit of objective improvement is the mean paired cost delta divided by direction-aware improvement magnitude. It is null for no improvement, tolerance-flat improvement, unavailable cost, or non-finite inputs; negative values are valid.

## Integrity and failures

The dedicated validator reconciles currency, duration, IDs, component sums, missing evidence, cost per completion, intervention separation/amortization, seed alignment, paired intersections, null rules, probabilities, trade-offs, sensitivity baseline deltas, zero-event retention, and result schema. Safe failures use the seven documented `economic_*` categories and contain no paths or stack traces.

## CG-6 / CG-7 decision overlay

Codegeist experiments remain a finite until-empty workload. Completions are comparable. Throughput and utilization are not cash denominators.

**Fixed workload:** busy-hour labor cost and attributable AI usage for the simulated demand. Subscription and extra-FTE payroll are omitted. ROI and payback are withheld.

**Recurring period:** requires expected demand per month. Calendar payroll = FTE × monthly loaded cost × selected months. Released hours and usage costs are scaled by demand × months / simulated completions. This is a linear per-case projection, not a re-simulated horizon.

Released human hours are not cash unless an explicit realization mechanism and rate are set. ROI is net / incremental investment when the period basis is valid and the denominator is positive. Payback uses the selected evaluation months, not a hardcoded year.

Financial-only break-even requires an explicit strategy. AI subscription sensitivity is undefined for hiring-only strategies.

