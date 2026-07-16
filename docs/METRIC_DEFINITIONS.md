# Metric Definitions

All durations use minutes. The measurement interval is `[a, b)` with duration `T = b - a`. For a step state `x(t)`, its time-weighted mean is `integral(x(t), a, b) / T`, calculated exactly from clipped event intervals.

## Observation population

- Window arrivals are items with `a <= createdAt < b`.
- Included items are window arrivals that complete successfully or fail terminally by `b`.
- Pre-warm-up items were created before `a`.
- Incomplete items are window arrivals not terminal by `b`.
- Active-at-end items are all items, including pre-warm-up items, not terminal by `b`.

Lifecycle averages use only included items. State areas use actual boundary state and therefore include any item active during the interval. Every count is returned explicitly in observation metadata.

## System metrics

- Arrival, completion, and failure rates divide their respective window event counts by `T`.
- Throughput is an alias of the successful completion rate.
- An included item's waiting and processing times are sums over its visits; average waiting and processing divide their population totals by the number of included items.
- Successful cycle time is final completion minus creation. Average and nearest-rank p95 use successful included items only.
- SLA attainment is successful included items at or below the applicable target divided by all included items; terminal failures do not attain SLA.
- Total rework counts accepted rework cycles for included items.
- Time-weighted WIP integrates created-but-not-terminal logical items.
- Time-weighted queue length integrates actually waiting resource requests across stages. Immediate grants never add queue area.
- Flow efficiency is included-population processing time divided by included-population cycle time; it is zero when the denominator is zero.
- Maximum queue length is the largest actually waiting count during the measurement interval.

Empty populations and zero denominators yield zero. `measurementDuration` is required to be positive, so state-rate denominators are non-zero.

## Stage metrics

Stage visit count includes visits belonging to the included item population. Completed processing, failures, and reworks are counted from those visits. Average waiting and processing use completed visits. Time-weighted queue length and maximum queue use all actual stage queue state during the interval, including carried state from pre-warm-up items.

Waiting-time share is the stage's included waiting total divided by the system included waiting total. Processing-time share is defined analogously. Empty denominators yield zero.

## Resource-pool metrics

- Total requests counts pool requests made during the measurement interval.
- Busy-capacity time is the integral of concurrent active capacity units.
- Available-capacity time is `capacity * T`.
- Utilization is busy-capacity time divided by available-capacity time.
- Idle-capacity proportion is `1 - utilization`.
- Busy time is retained as the busy-capacity-time value for contract continuity.
- Mean request wait averages waits for requests made during the interval.
- Maximum concurrent usage is the greatest active unit count and cannot exceed capacity.

## Analytical relationships

For a stable M/M/1 queue with arrival rate `lambda`, service rate `mu`, and `lambda < mu`: `rho = lambda / mu`, `W = 1 / (mu - lambda)`, `Wq = lambda / (mu * (mu - lambda))`, `L = lambda * W`, and `Lq = lambda * Wq`. Validation compares measured utilization, cycle/wait time, WIP, and queue length to these values after warm-up. Little's Law is checked independently using the measured completion rate: `L = throughput * W` and `Lq = throughput * Wq`.

## Repeated-run aggregation

Only successful ordinary-run scalar snapshots enter repeated aggregates. For `n` observations, Welford's recurrence computes the mean and sample variance `sum((x - mean)^2) / (n - 1)`; variance and standard deviation are zero for one observation. Minimum and maximum are exact. The p10, p50, and p90 fields use nearest rank: sorted position `ceil(p * n)`, clamped to `[1, n]`.

The mean confidence interval is the documented normal approximation `mean +/- z * sampleStandardDeviation / sqrt(n)`, using `z` values `1.6448536269514722`, `1.959963984540054`, and `2.5758293035489004` for confidence levels `0.90`, `0.95`, and `0.99`. It is marked reliable only at `n >= 30`; this flag is a disclosure, not a change to the calculation.

Threshold risk is `violating successful runs / successful runs`. SLA violates below its threshold; average cycle time, p95 cycle time, maximum queue, and terminal failure rate violate above theirs. Omitted thresholds produce no risk result. Failed runs never enter either denominator.

Representative selection uses system SLA attainment, average cycle time, p95 cycle time, time-weighted WIP, and total rework. Each dimension is min-max normalized across successful snapshots, with a zero contribution when its range is zero. Euclidean distance to the component-wise median determines the representative; lowest run index breaks ties. Its child seed is rerun and its scalar snapshot must exactly match the original before evidence is returned.

## Scenario comparison

Scenario value minus baseline value defines every absolute paired delta. A relative delta is `(scenario - baseline) / baseline`; a zero baseline yields `null` and increments the undefined count. Aggregation, nearest-rank percentiles, sample variance, and mean confidence intervals reuse the repeated-run formulas above and include only indexes where both variants succeeded.

Improvement direction is centralized per metric. Higher is better for SLA attainment, completion rate, and flow efficiency; the remaining objectives are lower-is-better. Differences within absolute tolerance `1e-9` are ties. Improvement, degradation, and tie probabilities divide by valid paired runs.

Paired risk reports baseline and scenario violation probability plus four reconciled quadrants: baseline-only, scenario-only, both, and neither. Resource-pool utilization deltas are factual paired evidence and do not imply an optimization direction. Guardrails use the scenario aggregate mean. Ranking considers only valid guardrail-passing scenarios and sorts by directed objective mean delta, probability of improvement, narrower confidence interval, then scenario ID.

## Sensitivity-derived evidence

Sensitivity aggregates selected system metrics with the existing repeated-run definitions and confidence method. Paired deltas and improvement/tie direction reuse the scenario-comparison registry. A finite difference is the change in aggregate mean divided by the change in adjacent tested parameter values. Observed elasticity normalizes both changes against absolute baseline magnitudes and is null under the zero/non-finite rules in `docs/SENSITIVITY_ANALYSIS_SPEC.md`. Monotonicity is an observed label over the tested successful values, not a mathematical or causal claim. Threshold crossings identify adjacent tested compliance transitions only and do not interpolate an exact parameter value.

## Economic evidence

Recurring operating cost is the sum of every configured available component for one measurement period. Resource provisioning is `capacity × measurement duration × rate`; stage visits, SLA violations, failures, rework, and completions use measured counts times supplied rates; queue and WIP holding use the time-weighted quantity times measurement duration and rate; fixed-period cost is added once. A configured unavailable source invalidates the total. Cost per completed item is recurring operating cost divided by completed items and is null at zero completions.

Paired economic delta is scenario recurring cost minus baseline recurring cost at the same run index. The relative denominator is the absolute baseline cost; zero baseline cost yields null and increments the undefined count. Lower/higher/tied probabilities use the `1e-9` absolute tolerance and divide by the successful economic intersection. Economic sensitivity finite differences, monotonicity, thresholds, and observed elasticity reuse the 0.6.0 discrete formulas.
