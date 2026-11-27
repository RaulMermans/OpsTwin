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

## CG-6 decision overlay (`cg6.v1`)

Codegeist experiments use a fixed-workload measurement basis. Completions are comparable across alternatives. Throughput, utilization, and resource-provisioning cost over until-empty horizons are not converted into monthly cash.

Staffing cash = modeled FTE × monthly loaded cost × evaluation months. Released human hours = reduction in simulated busy time and are not cash unless an explicit realization mechanism and rate are set.

Incremental investment = one-time implementation + incremental recurring spend versus baseline. Net benefit = realizable cash − incremental investment. ROI is that ratio when the denominator is positive, otherwise unavailable. Payback is reported only when cumulative incremental cash recovers implementation within the evaluation horizon.

Financial-only break-even reuses the same operational means. Coverage, processing reduction, and hybrid routing require a new operational experiment.

