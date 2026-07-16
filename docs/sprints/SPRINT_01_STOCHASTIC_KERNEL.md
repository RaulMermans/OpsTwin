# Sprint 01 Seeded Stochastic Kernel Implementation Plan

> **For agentic workers:** Execute inline with test-driven development. Do not commit or push. Keep the deterministic regression green after every behavior slice.

**Goal:** Replace the pre-public `0.1.0` model with a reproducible `0.2.0` multi-stage simulation kernel supporting bounded stochastic operations.

**Architecture:** Each run owns a SimPy environment, `random.Random`, event recorder, item states, resource registry, and metric evidence. Pydantic validates local and cross-record constraints before execution; JSON Schema remains implementation-neutral.

**Tech stack:** Python 3.12, SimPy, standard-library randomness, Pydantic, FastAPI, pytest, JSON Schema, Next.js, pnpm.

---

## Objective and current baseline

Sprint 00 provides one fixed source, stage, resource, deterministic event log, exact metrics, CLI, and health endpoint. Sprint 01 preserves those hand-calculated timings in a `0.2.0` equivalent while adding seeded stochastic and multi-stage behavior.

## In scope

- Run-local explicit or generated seeds.
- Fixed and Poisson arrivals.
- Fixed, exponential, uniform, and triangular processing.
- Multiple stages and resource pools, shared capacity, FIFO, and non-preemptive priority.
- Deterministic/probability/completion routes and bounded failure/rework.
- Expanded stable events, reconciled metrics, CLI, synchronous `/simulate`, contracts, examples, and golden tests.

## Out of scope

Monte Carlo aggregation, scenarios, persistence, recommendations, sensitivity, workflow editing, React Flow, charts, animation, authentication, deployment configuration, workers, external APIs, and LLM features.

## Assumptions

- Minutes remain canonical; fixed duration may be zero, stochastic duration parameters are positive.
- Poisson input uses positive mean inter-arrival minutes.
- Lower numeric priority means higher priority; equal priority is FIFO; processing is never preempted.
- `maximumReworkAttempts` is the number of rework cycles permitted after failures. A later failure is terminal and never silently completed.
- One success route exists per stage; failure routes are explicit deterministic stage routes.

## Architecture impact

- Replace single objects with source, pool, stage, route, and SLA collections.
- Add distribution sampling and route selection modules.
- Make run context own environment, random generator, recorder, states, and resource instances.
- Calculate metrics from item states and stage visits; expose pool metrics separately.
- Sprint 01.1 renamed the general-purpose engine module from `deterministic.py` to
  `simulator.py`; `run_simulation` executes both fixed and stochastic workflows.

## Contract changes

All public contracts use `schemaVersion: 0.2.0`. Runtime compatibility with `0.1.0` is intentionally removed under ADR-006. The result records seed, terminal failures, rework, stage visits, resource-pool metrics, and the expanded event envelope.

## Event changes

Retain the five lifecycle event types and add `RESOURCE_REQUESTED`, `RESOURCE_RELEASED`, `ROUTE_SELECTED`, `ITEM_FAILED`, and `ITEM_REWORKED`. `(simulationTime, sequence)` is canonical ordering. Expanded audit events intentionally increase deterministic event count without changing lifecycle times or metrics.

## Sprint 01.1 reconciliation

The neutral `simulator.py` module now names the stochastic-capable engine accurately. Internal execution, API responses, and CLI stdout serialize the same typed result model. Generated seeds use operating-system entropy outside the run generator, are returned, and reproduce the run when replayed; fixed distributions and deterministic routes do not advance that generator.

## Implementation sequence

- [x] Write `0.2.0` validation and deterministic regression tests; replace domain models and contracts.
- [x] Write exact distribution and seed tests; add run-local sampling.
- [x] Write multi-stage and routing tests; add context, recorder, states, and execution.
- [x] Write shared-pool and priority tests; add global pool registry and stable priority requests.
- [x] Write failure/rework-limit tests; add terminal-failure behavior.
- [x] Write metric, CLI, schema, example, and synchronous API tests; complete serialization.
- [x] Run `pnpm verify`, reproducibility proof, diff and scope audits, then update the scratchpad.

## Test plan

Use exact assertions for fixed models and standard-library seeded samples. Cover unsupported versions, empty collections, duplicates, references, probabilities, distributions, priorities, failure bounds, identical/different seeds, generated seed return, routes, shared capacity, non-preemption, FIFO ties, rework, terminal failure, no duplicate completion, reconciled metrics, contracts, CLI, health, and `/simulate`.

## Acceptance criteria

- `0.2.0` contracts and all cross-record validation reject invalid models.
- Fixed baseline retains Sprint 00 lifecycle timings and numerical metrics.
- Same seed gives identical events/metrics; a stochastic fixture differs under a different seed.
- All arrival, distribution, routing, shared-pool, priority, and bounded-rework behaviors are tested.
- `pnpm verify` and all GM-001 through GM-009 tests pass without deferred-scope features.

## Definition of done

Documentation matches behavior; examples and actual results validate; lint, types, tests, builds, CLI, API, and reproducibility checks pass; scans and Git review show only intended uncommitted work.

## Rollback plan

Stop on deterministic regression, separate schema failures from engine failures, return to the last green behavior slice without destructive Git operations, and reintroduce one tested primitive at a time. Never weaken exact golden assertions to mask incorrect behavior.
