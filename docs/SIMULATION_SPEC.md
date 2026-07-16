# Seeded Simulation Specification

## Contracts and run isolation

Operational models remain contract `0.2.0`. Simulation requests and results use contract `0.3.0`. Minutes are canonical. Every run owns its SimPy environment, `random.Random`, resources, event recorder, item states, and visits; mutable simulation state is never global.

## Arrivals, processing, and routing

- Fixed arrivals begin at `initialArrivalTime`; later items use a positive interval.
- Poisson arrivals sample exponential inter-arrival times from a positive mean.
- Priorities are non-negative integers: lower is higher, service is non-preemptive, and equal priorities retain FIFO order.
- Processing supports fixed, exponential, uniform, and triangular distributions with validated parameters.
- Each stage has one success route. Ordered route-option probabilities are in `[0, 1]` and sum to one within absolute tolerance `1e-9`.
- Fixed sampling and deterministic one-option routes consume no random values.

Item IDs are `<sourceId>-item-<one-based index>`. An explicit override wins over the model seed. Otherwise a model seed is used; if neither is present, operating-system entropy generates the returned replay seed. All stochastic choices use the run-local generator.

## Failure and rework

A stage may define a failure probability, failure route, and non-negative maximum rework attempts. Every failed visit records `ITEM_FAILED`. A failure within the allowance increments rework once, records `ITEM_REWORKED`, and follows the failure route without changing item identity or creation time. A failure beyond the allowance is terminal, produces no `ITEM_COMPLETED`, and is never forced to succeed.

## Resources and events

Stages referencing one pool share one capacity-constrained SimPy priority resource. Every visit preserves request, start, processing completion, and release evidence. `RESOURCE_REQUESTED.reason` is `waiting` only when the request actually queues and `immediate` when granted without delay.

The canonical event envelope is `simulationTime`, `sequence`, `eventType`, and `itemId`. Events may add source, stage, pool, route, target, priority, attempt, sampled duration, or reason. Sequence is strictly increasing and breaks equal-time ties. Contract list order controls source and route ties. A successful item emits `ITEM_COMPLETED` exactly once.

## Observation window

Requests accept `warmupDuration >= 0` and an optional positive `measurementDuration`.

- `simulationStart = 0`.
- `measurementStart = warmupDuration`.
- With an explicit duration, `measurementEnd = warmupDuration + measurementDuration`; otherwise it is `simulationEnd`.
- The finite simulation continues to terminal state for every generated item even if measurement ends earlier.
- Integration uses a closed-start/open-end interval `[measurementStart, measurementEnd)`; zero-duration transitions add no area.
- Pre-window events establish WIP, queue, and resource state at the boundary but add no measured area.

Item averages use items created within the window and terminal by its end. Pre-warm-up creations, incomplete in-window arrivals, and items active at the end are reported separately. State metrics may include pre-warm-up items because their real state carries into the window.

## State integration and metric evidence

Streaming observation integrates canonical step functions clipped to the measurement interval. WIP rises at creation and falls at successful or failed terminal state. Stage queue rises only on an actually waiting request and falls at processing start. Pool usage rises at processing start and falls at release. Each event also updates a compact audit ledger. Integrity validation runs on the complete ledger before metrics are returned; it does not require retaining every event object.

## Result detail

- `summary` returns no event records and is the API/CLI default.
- `sampled` returns all events for up to `sampleLimit` item IDs selected deterministically.
- `full` returns the complete canonical event stream.

Sampling ranks predictable source item IDs by SHA-256 of `seed:itemId`, then item ID, and selects the lowest ranks before execution without consuming pseudorandom draws. At emission, summary retains no event objects, sampled retains complete histories only for selected items, and full retains every event. All modes preserve canonical ordering, metrics, total event counts, and integrity behavior. Direct engine calls default to full detail for diagnostic compatibility.

## Repeated runs

Repeated simulation uses separate request/result contract `0.4.0` and the semantics in `REPEATED_RUN_SPEC.md`. Child seed `i` is the unsigned big-endian integer represented by the first eight SHA-256 bytes of the UTF-8 text `<baseSeed>:<i>`. Runs are sequential. Ordinary runs always use summary detail and retain only scalar snapshots; one deterministic median-vector representative is rerun with configured detail. Aggregates exclude explicitly reported failures and require the configured minimum successful-run ratio.

## Scenario comparison

Scenario comparison uses separate request/result contract `0.5.0` and the semantics in `SCENARIO_COMPARISON_SPEC.md`. Approved scalar fields are replaced by entity identity through a centralized registry; arbitrary paths and topology changes are forbidden. Each scenario is materialized from a deep copy, fully validated, and canonically hashed. Baseline and scenarios share the deterministic child seed at each run index and execute sequentially in baseline-then-request-order. Paired evidence uses successful-index intersections. Ordinary runs are summary-only; representative evidence is bounded to baseline and the top eligible ranked scenario.

## Exclusions

Shifts, costs, persistence, dynamic priorities, preemption, conditional expressions, background execution, parallel execution, automated recommendations, and deployment behavior are not supported.
