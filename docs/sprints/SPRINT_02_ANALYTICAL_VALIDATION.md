# Sprint 02 Analytical Validation Implementation Plan

> **For agentic workers:** Execute inline with test-driven development. Do not commit or push. Preserve all Sprint 01 golden models.

**Goal:** Define precise observation semantics, calculate time-weighted operational metrics, validate simulation integrity, and compare stochastic results with known analytical queueing behavior.

**Architecture:** Operational models remain `0.2.0`; execution request and result contracts become `0.3.0`. The simulator produces complete canonical evidence, observation and metric modules integrate that evidence over an explicit window, integrity validation runs before return, and deterministic post-run filtering produces bounded result detail without consuming simulation randomness.

**Tech stack:** Python 3.12, SimPy, Pydantic, FastAPI, standard-library randomness/hash/statistics/timing, pytest, JSON Schema, pnpm.

---

## Objective and current baseline

Sprint 01.1 provides a neutral seeded simulator with fixed/Poisson arrivals, four processing distributions, routing, shared pools, priorities, bounded rework, typed CLI/API output, 53 tests, and exact deterministic/stochastic reproduction. Current metrics use the complete run horizon and do not support warm-up exclusion or bounded payload modes.

## In scope

- Explicit warm-up and measurement windows.
- Time-weighted WIP, queue, and busy-capacity integration.
- Windowed arrival/completion/failure rates, lifecycle averages, flow efficiency, stage shares, and resource wait/utilization.
- Automatic post-run integrity validation.
- M/M/1, Little's Law, distribution-moment, route, and failure convergence checks.
- `summary`, `sampled`, and `full` result detail.
- Reproducible 100/1,000/10,000-item performance and payload measurements.

## Out of scope

Monte Carlo scenario aggregation, scenario comparison or persistence, recommendations, sensitivity, workflow editing, React Flow, charts, animation, databases, authentication, deployment configuration, background jobs, external integrations, and LLM features.

## Assumptions

- Minutes remain canonical and simulation time begins at zero.
- Operational workflow structure remains schema `0.2.0`.
- A finite source run continues until every created item is completed or terminally failed, even when measurement ends earlier.
- Canonical event order is `(simulationTime, sequence)` and events express all state transitions required for integration.
- Window boundaries use closed-start/open-end state integration; zero-duration transitions contribute zero area.

## Observation-window semantics

- `simulationStart = 0`.
- `measurementStart = warmupDuration`.
- With explicit duration, `measurementEnd = warmupDuration + measurementDuration`; otherwise it is the final terminal event time.
- `simulationEnd` is the time all generated items become terminal and may exceed `measurementEnd`.
- Events before measurement start establish the real boundary state but contribute no area.
- State integration stops at measurement end.
- Item-level averages include only items created at or after measurement start and terminal by measurement end.
- Items created before the window and items incomplete at measurement end are counted separately, never silently mixed into averages.

## Metric semantics

For step state `x(t)` and window length `T`, the time-weighted average is `sum(x * duration) / T` over clipped intervals. WIP rises on creation and falls on successful or failed terminal state; stage queue rises on queue entry and falls on process start; pool usage rises on process start and falls on release.

- Arrival/completion/failure rates divide respective window counts by `T`.
- Flow efficiency is total processing time divided by total cycle time for the included item population.
- Resource utilization is busy-capacity area divided by `capacity * T`; idle proportion is one minus utilization.
- Stage waiting/processing shares divide stage totals by corresponding system totals.
- Existing deterministic results remain exact for zero warm-up, inferred full horizon, and a fully terminal population.

## Contract changes

- `operational-model.schema.json` remains `0.2.0`.
- `simulation-request.schema.json` becomes `0.3.0` and adds `seedOverride`, `observation`, and `resultDetail`.
- `simulation-result.schema.json` becomes `0.3.0` and adds observation metadata, expanded metrics, integrity status, and result-detail counts/selection.
- API defaults to summary; direct engine tests may request full explicitly.

## Architecture impact

- `observation.py` integrates canonical state transitions and selects measurement populations.
- `metrics.py` remains the formula boundary and consumes observation evidence.
- `integrity.py` validates lifecycle, event, route, and resource invariants after execution.
- `result_detail.py` filters complete valid results post-run using stable hashes.
- API and CLI remain stateless transports around the same typed result.

## Test plan

Use red-green slices for GM-010 through GM-018. Exact deterministic fixtures cover queue/WIP/resource areas and boundaries. Fixed-seed long-run fixtures compare M/M/1 and Little's Law with documented relative tolerances. Direct malformed evidence fixtures test integrity errors. Statistical primitive tests use bounds, expected moments, fixed seeds, and explicit tolerances rather than fragile exact long sequences.

## Analytical benchmark formulas

For M/M/1 arrival rate `lambda`, service rate `mu`, and `lambda < mu`:

```text
rho = lambda / mu
W   = 1 / (mu - lambda)
Wq  = lambda / (mu * (mu - lambda))
L   = lambda * W
Lq  = lambda * Wq
```

Little's Law checks compare `L` with measured completion rate times `W`, and `Lq` with measured completion rate times `Wq`, only for the documented stable window.

## Performance-baseline method

Run one bounded deterministic benchmark model at 100, 1,000, and 10,000 items with a fixed seed. Measure execution and JSON serialization separately, record canonical event count and payload bytes for summary/full plus sampled at 10,000, include environment versions, and make no hardware-independent or Vercel-safe claims.

## Implementation sequence

- [x] Request/result `0.3.0` validation and schemas.
- [x] Observation boundary and exact state-area integration.
- [x] Windowed system, stage, and resource metrics.
- [x] Automatic structured integrity validation.
- [x] Deterministic result-detail modes, API, and CLI.
- [x] M/M/1, Little's Law, primitive, route, and failure validation.
- [x] Benchmark command and measured baseline.
- [x] Final full verification and repository audits.

## Acceptance criteria

All AC1–AC9 in the work package pass: Sprint 01 remains green; observation populations are explicit; state metrics are time-weighted; integrity failures are structured; M/M/1/Little's Law/statistical checks meet documented tolerances; detail modes preserve core metrics; 100/1,000/10,000 measurements are recorded; all quality gates pass; and deferred product/deployment scope is absent.

## Definition of done

GM-010 through GM-018, all prior tests, examples, schemas, API/CLI modes, integrity checks, full benchmark, builds, `pnpm verify`, diff/secret/path/generated-artifact audits, documentation, and scratchpad are complete with no commit or push. Sprint 02.1 subsequently replaced full-event internal retention in summary/sampled modes with the compact audit ledger and streaming observation described by ADR-008; public `0.3.0` semantics remain unchanged.

## Rollback plan

Stop on a Sprint 01 regression. Separate observation boundaries from formulas, restore the last green slice without destructive Git operations, and reintroduce one collector or contract field at a time. Preserve accurate failing mathematical tests and never remove integrity checks to mask incorrect evidence.
