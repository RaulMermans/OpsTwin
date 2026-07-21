# Architecture

## System overview

OpsTwin separates the product interface from a Python simulation service. Versioned JSON contracts form the language-neutral boundary, and a normalized event log is the evidence from which metrics are calculated.

## Text architecture diagram

```text
Browser -> Next.js web (foundation only)
                 future typed HTTP boundary
Operational JSON -> FastAPI/Pydantic -> SimPy simulator -> event emitter
                                                     -> compact audit ledger
                                                     -> streaming observation
                                                     -> retained requested detail
                                                     -> integrity + metrics -> result JSON

Repeated request -> deterministic seed schedule -> sequential summary runs
                                                  -> scalar snapshots/online moments
                                                  -> risks + convergence
                                                  -> one representative rerun -> result JSON

Comparison request -> immutable baseline + identity overrides -> validated variants
                   -> shared seed schedule -> baseline then scenarios per run index
                   -> paired intersections/deltas/risks -> guardrails + ranking
                   -> at most two representative reruns -> result JSON

Economic comparison -> existing comparison coordinator + per-run observer
                    -> pure explicit-assumption scalar cost snapshots
                    -> existing aggregation + paired economic intersections
                    -> intervention separation + factual trade-off evidence

Economic sensitivity -> existing 0.6.0 sensitivity coordinator + per-run observer
                     -> cost response curves without a second simulation sweep
```

## Current local architecture

The web app provides a landing page and a client-side Scenario Lab. A narrow TypeScript mapper creates approved model copies and guided identity overrides; session state manages stable scenario identities and invalidates stale evidence. A separate immutable workflow presentation adapter maps stable model IDs to deterministic frontend-only nodes, edges, terminals, resource links, changes, and evidence overlays. Presentation adapters format and organize runtime-checked, server-owned comparison evidence. Sanitized JSON/CSV and print output are browser-local. The Python application validates a collection-based operational model and creates an isolated seeded SimPy run context. Each emitted event updates a compact audit ledger and streaming observation collector; only requested evidence is retained. There is no database, worker, graph engine, or external service.

## Deployment architecture

Root `vercel.json` defines one current Vercel Services project containing the Next.js interface and bounded FastAPI simulation function behind one public boundary. `/api/simulation/(.*)` routes to FastAPI while the catch-all routes to Next.js; the original path is preserved. ADR-014 was accepted on 2026-07-20 after Sprint 11's production deployment validated this configuration at `https://ops-twin.vercel.app` (see `docs/VERCEL_DEPLOYMENT.md` and `docs/VERCEL_PREVIEW_EVIDENCE.md`). PostgreSQL remains a future direction only.

## Component responsibilities

- `apps/web`: Scenario Lab presentation, scenario session state, canonical form/scenario/guardrail mapping, deterministic read-only workflow presentation, bounded client validation, runtime-checked same-origin transport, safe result adapters, and sanitized local exports; never simulation mathematics.
- `app/domain`: validated operational inputs, cross-record rules, and typed result records.
- `app/engine`: run context, sampling, routing, neutral `simulator.py` execution, compact event auditing, streaming observation, metric derivation, deterministic result-detail selection, seed scheduling, scalar snapshots, aggregation, risks, convergence diagnostics, and representative selection with no global run state.
- `app/main.py`: HTTP transport.
- `app/cli.py`: local example transport.
- `contracts`: implementation-neutral public boundaries.

## Interface boundaries and data flow

Input JSON is validated before execution. Each single run owns its seed, environment, resources, item states, visits, compact ledger, collector, and requested retained events. Deterministic sampled item IDs are selected before execution without consuming run randomness. Complete event truth is audited and observed at emission, while retention changes only event-object volume.

A repeated request derives an index-stable child-seed schedule, executes ordinary runs sequentially in summary mode, and discards each result after extracting a scalar snapshot. Online moments and bounded value lists support aggregates, confidence intervals, risks, and convergence checkpoints. One run nearest the normalized median metric vector is rerun with caller-selected bounded detail and verified against its original scalar snapshot. Failed runs are categorized safely and excluded from aggregates; the minimum-success policy prevents a misleading partial result.

A comparison deep-copies the baseline for each validated identity-based override set and preserves topology. For every run index it executes the baseline once, then each valid scenario sequentially with the same child seed. Only intersecting successful indexes contribute to paired statistics. Invalid or under-ratio scenarios remain visible but unranked. Guardrails determine eligibility; deterministic objective/probability/interval/ID ordering is labelled comparative ranking, not a recommendation. Ordinary results retain no events, and only baseline plus top-ranked scenario representatives may be retained.

## Failure handling

Validation rejects unsupported units and invalid ranges with structured details. No partial result is presented as complete. The health endpoint does not claim dependency health because Sprint 00 has none.

## Security baseline

No secrets, authentication, user data, remote execution, or persistence exist. Dependencies are lockfile-pinned, inputs are bounded and validated, and CI runs static checks and tests.

## Observability baseline

The canonical event stream, returned seed, integrity status, observation metadata, and total/included evidence counts provide reproducible run evidence. API access logging uses server defaults; structured telemetry is deferred.

## Deferred infrastructure

Vercel deployment configuration, PostgreSQL, authentication, workers, Redis, Celery, Docker, and production telemetry are deferred.

## Proposed future ADRs

Persistence model, API versioning, durable run execution, and random-stream compatibility across future algorithm changes require ADRs before adoption.

## Sensitivity analysis boundary (`0.6.0`)

Sensitivity is a sibling orchestration boundary, not an extension of scenario comparison. `app/sensitivity/registry.py` supplies metadata while delegating mutation to the scenario override registry; materialization reuses immutable scenario primitives; coordination reuses seed scheduling, summary simulation, scalar snapshots, aggregation, paired-delta formulas, and metric directions. Execution order is run index then canonical tested value, so the baseline value runs once per index. Pure analytics produce discrete finite differences, elasticity, monotonicity, and adjacent threshold intervals. A separate integrity validator reconciles 24 invariants before serialization. FastAPI, CLI, and the in-place Scenario Lab consume the same typed result.

## Economic evidence boundary (`0.7.0`)

Economics is a sidecar over successful summary runs. Optional observers on the existing comparison and sensitivity coordinators evaluate one pure scalar cost snapshot before each ordinary result is discarded. `app/economics/registry.py` owns formulas and source metadata; the evaluator owns missing-evidence semantics; aggregation reuses existing statistical primitives. Economic comparison consumes operational objective evidence already returned by comparison and cannot change its ranking. Economic sensitivity calls the 0.6.0 coordinator exactly once. One-time intervention amounts remain separate unless a positive amortization period is explicit. No events, persistence, inferred assumptions, or finance forecast enter this boundary. An unexpected observer evaluation failure no longer disappears silently: `EconomicExecutionMetadata.observerFailures` records a bounded, categorized, safe-message entry per failed run without ever exposing a traceback or path, and without affecting the operational comparison it observes.

## Playback presentation boundary (Sprint 10)

Playback adds no backend execution. `apps/web/lib/playback/` is a pure TypeScript adapter chain — normalize -> timeline -> controller/journey/export — that reconstructs deterministic frames entirely client-side from the `events` array already carried by the retained `RepresentativeRunResult` in contracts `0.4.0`/`0.5.0` (ADR-021, ADR-022). No new backend route, WebSocket, or event semantic is introduced; reconstruction only re-derives presentation state (stage/resource/item occupancy) from the existing `EventType` vocabulary. The playback panel is a read-only consumer of a comparison result the workspace already fetched and never issues its own request.

## Local packaging and development boundary (Sprint 09.1)

`scripts/package-source.mjs` and `scripts/verify-source-package.mjs` build and check a deterministic, size-bounded source archive using `git ls-files` plus a defensive forbidden-path filter and a hand-rolled minimal ZIP writer (no external archiver dependency; Node has no built-in ZIP container writer). `scripts/dev-local.mjs` and `scripts/smoke-local.mjs` spawn `apps/simulation-api` (`uvicorn`) and the `next` binary directly, set `OPSTWIN_DEV_API_ORIGIN` automatically, and fail clearly on a port conflict instead of silently choosing another port.

## Guided presentation boundary (Sprint 12)

Guided and Advanced are session-local presentation modes in the same workspace. They share baseline state, scenario state, comparison request, endpoint, response, integrity evidence, and exports. Guided selectively discloses existing controls and renders response-owned objective direction, paired deltas, probabilities, and intervals; it adds no analytics or transport logic.
