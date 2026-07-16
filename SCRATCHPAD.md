# OpsTwin Scratchpad

## Active milestone

Sprint 07 controlled workflow visualization is implemented locally over the unchanged operational `0.2.0` and comparison `0.5.0` contracts. Sprint 06.1 recovered source-level evidence but the managed environment still blocks frontend test startup, completed builds, local runtime, and browser QA.

- Canonical emission now updates a compact audit ledger and streaming observation collector.
- Summary retains zero event objects, sampled retains selected-item events only, and full retains every event.
- At 1,000 items, summary retention fell from 8,000 events and about 13.4 MB traced peak to zero events and 3.07 MB; sampled limit 25 retained 200 events at 3.25 MB.
- Repeated requests execute deterministic child seeds sequentially, aggregate successful scalar snapshots, report risk/failures/convergence, and rerun exactly one representative seed.
- Sprint 03 final `pnpm verify` passed 141 tests, both builds, the canonical example, and both benchmark smokes.
- Sprint 04 final `pnpm verify` passed 183 tests, both builds, the canonical example, and all three benchmark smokes.

## Current sprint

Sprint 07 - Controlled Workflow Visualization.

## Current status

Operational models remain `0.2.0`; single-run contracts remain `0.3.0`; repeated contracts remain `0.4.0`; scenario comparison adds separate `0.5.0` contracts. Scenario models use approved identity-based replacements, paired shared seeds, failure isolation, comparative metrics, explicit guardrails, deterministic eligibility/ranking, and at most two representatives.

The workflow view uses an immutable typed presentation adapter, stable frontend-only positions, explicit scenario overrides, and backend-returned stage/resource aggregates. It does not alter requests or simulation calculations.

## Completed

- Sprint 01.1 reconciliation: renamed the misleading deterministic engine module to `simulator.py`, aligned CLI serialization, seed behavior, API/contracts, docs, and preserved all prior golden models.
- Warm-up and optional measurement duration with explicit population metadata and carried boundary state.
- Time-weighted WIP, stage queue, and resource busy-capacity metrics; windowed rates and lifecycle/flow-efficiency metrics.
- Sixteen automatic evidence-integrity invariants over complete compact evidence before metrics return, with safe structured transport failures.
- Summary, deterministic sampled, and full result detail; API/CLI default to summary and direct engine diagnostics default to full.
- GM-010 through GM-018: exact state areas, window boundaries, M/M/1, Little's Law, malformed evidence, route/failure convergence, detail invariance, and scaling evidence.
- Full 100/1,000/10,000-item benchmark recorded in `docs/PERFORMANCE_BASELINE.md`; verify includes a smoke benchmark.
- Emission-time retention with zero summary event objects, bounded selected-item sampled evidence, and unchanged full evidence.
- GM-019 through GM-029: repeated reproducibility, seed schedule, moments, quantiles, confidence intervals, risks, representative selection, failure policy, bounded retention, convergence, and performance.
- Separate `0.4.0` repeated schemas, synchronous API route, CLI command, full benchmark matrix, ADR-009, and ADR-010.
- Sprint 03.1 child-process Node resolution and strict zero-event ordinary-run retention metadata.
- ADR-011 through ADR-013, `0.5.0` comparison contracts, safe materialization, shared-seed execution, paired deltas/risks, guardrails, ranking, API/CLI, example, integrity, and comparison benchmark.
- Sprint 06.1 runtime recovery record with one-shot root preflight and targeted verification evidence.
- Sprint 07 Flow integration with canonical source/stage/route/resource/terminal mapping, rework styling, four display modes, entity inspection, visible list equivalent, and mobile fallback.
- ADR-015 proposed pending executable frontend tests; ADR-016 accepted for evidence-only visual overlays.

## Decisions made

- Operational workflow structure remains schema `0.2.0`; execution envelopes advance to `0.3.0`.
- Observation state uses closed-start/open-end exact integration and preserves pre-warm-up state.
- Lifecycle averages include only in-window creations terminal by measurement end; excluded populations are explicit.
- Queue area counts actual waiting only; immediate resource grants add no queue area.
- Complete evidence is audited and observed at emission; only requested event objects are retained.
- Sampled item selection ranks SHA-256 of `seed:itemId` and consumes no simulation randomness.
- Benchmarks characterize the measured local environment only and make no hosting capacity claim.
- Repeated runs are sequential; ordinary runs are summary-only and discarded after scalar snapshot extraction.
- Child seeds use the first unsigned big-endian 64 bits of SHA-256 over `<baseSeed>:<runIndex>`.
- Representative selection uses normalized distance to the median five-metric system vector and lowest-index tie-breaking.
- Workflow structure is read-only and deterministic; no graph dependency, layout persistence, or editing surface is introduced.
- Overlay intensity is presentation-only min/max scaling over visible finite backend values; raw evidence remains visible and missing values remain unavailable.

## Commands verified

- Sprint 07 direct frontend TypeScript (`tsc --noEmit`) and ESLint (`eslint . --max-warnings=0`) pass using the bundled Node executable, including the new workflow source and tests.
- Focused Node runtime checks pass exact canonical mapping, deterministic layout/path output, baseline immutability, explicit resource/route/SLA change mapping, and overlay min/max/equal/missing scaling.
- Next production compilation succeeds, then its post-compile child process is blocked with `spawn EPERM`.
- Direct Python regression execution completed 185 passing tests; nine CLI tests were blocked at setup because pytest could not access `apps/simulation-api/pytest-of-rmermans`.
- Sprint 06.1 one-time `pnpm bootstrap` and `pnpm verify` attempts reproduced the inherited managed-sandbox failures and were not retried.
- Targeted root lint and typecheck pass. Root web tests fail before collection at Vite `spawn EPERM`; root build fails creating a Python isolated build environment. The isolated web build compiles successfully and then fails spawning Next's TypeScript worker.
- `next dev` fails immediately with `spawn EPERM`; the entire browser and viewport QA group remains blocked.
- Sprint 01.1 `pnpm verify` with all 53 prior tests.
- Final `pnpm verify`: ruff, ESLint, mypy over 23 source files, TypeScript, 141 pytest tests, Python `0.4.0` distribution build, Next.js production build, canonical CLI example, and both benchmark smokes.
- Focused observation, integrity, result-detail, analytical, schema/API/CLI, and benchmark tests.
- Full `pnpm benchmark:simulation` at 100, 1,000, and 10,000 items.
- Full `pnpm benchmark:repeated` at 100 items × 10/100 runs and 1,000 items × 10/50 runs.
- Full `pnpm benchmark:comparison` at the required four matrices, with 1.0 paired ratios, at most two retained representatives, and passing integrity.
- Fresh-shell `pnpm bootstrap` passed without manual Node `PATH` repair.
- Deterministic GM-002 exact values and 40 events preserved.
- Same-seed full-result SHA-256 equality and different-seed divergence.
- `git diff --check`, secret/path scans, ignored generated-artifact review, and empty cached diff.

## Known issues

- The managed sandbox blocks pip temporary build trackers/build environments, Node/Vite/Next child-process spawning, `pnpm bootstrap`, `pnpm verify`, Vitest startup, Next build/dev startup, and therefore local browser QA. Inaccessible inherited and newly created failed-bootstrap/build temporary directories remain untouched.
- Vercel CLI 56.2.0 `dev -L` recognizes both Services but emits an unescaped Windows path in generated Python bootstrap code.
- Preview validation is deliberately deferred by user instruction. No preview or production deployment was created.

## Next action

Resolve or explicitly authorize a workspace environment that permits child processes and temporary-directory access, then rerun frontend tests, build, full verification, and Flow browser QA at the three required viewports. Await explicit instructions before any Vercel, GitHub, commit, push, or other remote action.

## Last updated

2026-07-16

## Sprint 07.1 / Sprint 08 local checkpoint — 2026-07-16

- Workflow change mapping now matches backend route-option identity and resolves fixed arrivals, processing parameters, failure probability, and rework attempts without layout changes.
- Sensitivity `0.6.0` is OFAT only: explicit baseline value, canonical execution order, shared run-index seeds, scalar snapshots, no representatives, no interpolation, no optimization.
- Root bootstrap/verify/build remain blocked by inaccessible isolated Python directories; Vitest remains blocked by `spawn EPERM`. Direct focused backend sensitivity tests are executable.
- Local-only boundary remains active: zero staging, commits, remotes, GitHub, Vercel linking, or deployment.

## Sprint 08.1 / Sprint 09 local checkpoint — 2026-07-16

- Sensitivity result schema now mirrors the typed 0.6.0 result recursively, rejects unknown nested fields, uses finite numeric bounds, and validates live API plus canonical request/result evidence. The focused sensitivity/economics suite passes 50 tests.
- Economics 0.7.0 accepts only explicit finite non-negative assumptions in one currency/time unit. The pure evaluator covers resource capacity, stage visits, queue/WIP holding, SLA violations, failures, rework, completion, and fixed period cost with unavailable/not-configured distinctions.
- Paired economics observes the existing comparison runs; economic sensitivity observes one existing 0.6.0 sweep. Both retain scalar snapshots only, preserve work budgets, and report 23–24 integrity checks with zero ordinary retained events.
- One-time intervention costs remain separate unless explicit positive amortization periods are supplied. Cost/objective language is factual and does not change operational ranking.
- Full serial economic comparison and economic sensitivity benchmark matrices executed locally with 1.0 paired ratios, zero retained events, and passing integrity; measurements are recorded in `docs/ECONOMIC_PERFORMANCE.md`.
- Root bootstrap, aggregate verify, Python build, Vitest, and global pytest fixture setup remain affected by the documented managed Windows temporary-directory/child-process restrictions. Inaccessible temporary directories remain untouched and no escalation was attempted.
- Local-only boundary remains active: no staging, commit, push, GitHub action, Vercel link/project, preview, or production deployment.

## Repository publishing and CI — 2026-07-16

- Private GitHub repository `RaulMermans/OpsTwin` now contains the initial project import and the CI repair commit.
- Web CI repairs make Vitest mocks hoist-safe, clean the document between tests, use canonical route-option identities, restore inspector focus, and avoid delayed timeout rejections.
- GitHub Actions CI passed in full for commit `1d38a73` after the repair.
