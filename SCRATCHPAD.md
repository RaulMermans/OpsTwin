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

Sprint 11 - Vercel Production Recovery, Runtime Verification, and Flagship Product Polish. See the dated checkpoint below for current status; earlier "Current sprint"/"Next action" text below is historical (append-only log convention).

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

## Sprint 14 local checkpoint — 2026-07-21

- Began the plain-language and Flow repair over the unchanged simulation and
  comparison contracts.
- Identified the Flow collapse as a CSS grid minimum-track/hidden-overflow
  issue; the in-progress repair moves the change summary into the layout
  grid, protects canvas width, and stacks the layout below desktop widths.
- Added centralized Guided metric labels, percentage-point formatting,
  returned-interval interpretation, input help, evidence-tab wording, and
  local regression tests. `pnpm typecheck` passed using Node 22.22.3.
- The focused Vitest command reported 100 passing tests but exited non-zero
  because nine fork workers timed out at startup. Browser, manual, screenshot,
  production, and full verification work remain pending; no deploy or
  participant study has been claimed.

## Sprint 14.1 closure attempt — 2026-07-22

- Guided nested panels now have business-first labels for comparison settings,
  Process, Test assumptions, Costs, and glossary entries; Advanced retains the
  technical vocabulary.
- Guided paired deltas use the central metric formatter, so proportion deltas
  are shown as percentage points. The comparative sentence now says which
  change had the higher average separately from whether its returned plausible
  range is favorable, inconclusive, unfavorable, or unavailable.
- Focused Vitest cannot collect tests on this host: Vite fails while loading
  installed `picomatch@4.0.5` with `TypeError: parse.fastpaths is not a
  function`. `pnpm install --frozen-lockfile` and `--force` both completed but
  did not repair the package. The subsequent typecheck invocation produced
  only its startup line before the managed runner stopped returning completion
  output. Browser measurements, rendered regression, owner QA, screenshots,
  deployment, production QA, and commits/pushes are intentionally pending.

## Sprint 12 — first-time usability checkpoint — 2026-07-20

- Recorded a simulated/expert first-time-user audit before changes; no human participant testing has been claimed.
- Guided is now the default session presentation over the unchanged baseline, scenarios, 50-run paired request, response, integrity, and exports. Advanced preserves the prior editing surface.
- Results render immediately after the run panel with response-direction-aware paired deltas, probabilities, uncertainty, non-prescriptive language, and links to deeper evidence.
- Added first-run orientation, accessible native glossary, prerequisite copy for unavailable evidence, and a concrete guided landing path.
- `pnpm lint`, `pnpm typecheck`, `pnpm test` (247 backend + 142 web tests), `pnpm test:web`, `pnpm build`, and `pnpm verify` all pass after allowing pnpm's managed temporary runtime. `pnpm smoke:preview -- https://ops-twin.vercel.app` passes against the existing deployment; no Sprint 12 deployment was created.

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

## Sprint 11 — Vercel production recovery and flagship verification — 2026-07-20

- Root cause of the failing `ops-twin` production deployment (commit `fd1c3f4`): `apps/web/lib/templates/support.ts` imported `../../../../examples/product/support-operations-baseline.json`, a path `.vercelignore` excludes, so Turbopack failed with `Module not found` once Vercel stripped `examples/`. Fixed by packaging a runtime copy inside `apps/web/lib/templates/` and adding `pnpm verify:vercel-runtime` (wired into `build:vercel`/`verify`). Also fixed a `--`-argument-handling bug in `pnpm smoke:preview`/`smoke:vercel-local`.
- New environment note: this session ran on a macOS host with Node 22.22.3 (via `nvm`, not the default Node 20 on `PATH`)/pnpm 11.7.0/Python 3.12.13 (via `.local/bin/python3.12`, not the default `python3` 3.11). With those toolchains, the environment blocker recorded against every prior sprint did not reproduce: `pnpm verify` passed completely for the first time in this project's history (ruff, ESLint, mypy, `tsc`, backend pytest 247/247, Vitest 18/18 files and 140/140 tests, both builds, canonical example, all six benchmark smokes, source packaging).
- Deployed the hotfix to the existing `ops-twin` Vercel project (Services model, `web` + `simulation`, one domain `https://ops-twin.vercel.app`) via the existing GitHub integration — no new project, repo, or architecture. All public routes and six analysis endpoints verified live with passing integrity at bounded run counts; `pnpm smoke:preview` passed; full browser product journey (comparison, Flow, Sensitivity, Economics, Playback, exports) verified with zero console/network errors at 390×844/768×1024/1440×900 with no page-level horizontal scroll and zero accessibility violations found. ADR-014 accepted; GM-051 passes; GM-053–140 reconciled in `docs/VALIDATION_PLAN.md`.
- Hardened the economic-sensitivity observer (`apps/simulation-api/app/economics/sensitivity.py`) to record safe, categorized `EconomicSensitivityObserverFailure` evidence instead of a bare `except Exception: <count only>`, mirroring the Sprint 09.1 comparison-observer pattern; additive `0.7.0` contract field, focused regression test, schema updated and validated by the existing schema-parity test.
- One suspected UX defect (economics negative-input validation appearing to lack a visible error) was investigated and found to be a false alarm — the `role="alert"` message exists; no code change was needed. Full detail, remaining limitations (GM-136 reduced-motion, GM-138 payload boundary unchanged), and the Results-panel-at-bottom layout observation (intentionally left unchanged as an architecture-level decision, not a bug) are in `docs/sprints/SPRINT_11_RUNTIME_AND_FLAGSHIP_POLISH.md`.
- Local-only boundary is now lifted for this sprint by explicit user authorization: commits were pushed to `origin/master` and the existing Vercel project was deployed to and validated.

## Sprint 09.1 / Sprint 10 local checkpoint — 2026-07-18

- New environment: this session ran on a fresh macOS host (not the previously documented managed Windows sandbox). `pnpm`/corepack was unusable (`pnpm@11.7.0` requires Node >=22.13; the installed Node was 20.20.0), so all root `pnpm` commands were exercised by invoking the underlying local binaries directly (`.venv/bin/python -m {pytest,ruff,mypy}`, `apps/web/node_modules/.bin/{tsc,eslint,vitest}`) instead. The repository's committed `.venv` was a corrupted cross-platform artifact (mixed Windows `.pyd`/POSIX layout, Python 3.11 instead of the pinned 3.12) that hung on any import touching a compiled extension; it was recreated from a local Python 3.12.13 interpreter and reinstalled from `requirements.lock`, which resolved the hang.
- Vitest's worker pool (`forks` and `threads`) times out starting a worker in this sandbox; frontend test execution is blocked by environment for that reason, not by product defects. `tsc --noEmit` and a full `pnpm exec eslint` run were also extremely slow under the sandbox's background-process throttling; both were kicked off and their results are recorded in the session's final report rather than blocking further work.
- Sprint 09.1: added deterministic `pnpm package:source`/`pnpm verify:source-package` (hand-rolled minimal ZIP writer, no new dependency, `git ls-files` plus a defensive forbidden-path filter), one-command `pnpm dev`/`pnpm smoke:local` (`scripts/dev-local.mjs`/`scripts/smoke-local.mjs`, spawning `uvicorn` and the `next` binary directly rather than through `pnpm`, with `OPSTWIN_DEV_API_ORIGIN` set automatically and port-conflict detection), decomposed `workspace.tsx` (334 -> 214 lines) into `components/results/results-panel.tsx` and `lib/scenario-lab/scenario-labels.ts` with no behavior change, and hardened the economics comparison observer (`EconomicObserverFailure` on `EconomicExecutionMetadata.observerFailures`, contract-additive, categorized/safe-message, isolated from operational comparison) with a focused test proving isolation and safe-message content.
- Sprint 10: added a pure TypeScript playback core (`apps/web/lib/playback/{types,normalize,timeline,controller,important-events,journey,export}.ts`) that reconstructs deterministic frames client-side from the existing retained `RepresentativeRunResult.result.events`, with no new backend contract (ADR-021, ADR-022). Wired into the workspace as `components/playback/playback-panel.tsx` (controls, event ledger, item journey, baseline/scenario toggle with paired-identity disclosure, fixed representative disclaimer, reduced-motion timer gating, JSON export). `pnpm benchmark:playback` executed locally and recorded `docs/PLAYBACK_PERFORMANCE.md`.
- Full backend `pytest` (246 tests, including the new economics observer test) passed after the `.venv` recreation. `ruff check apps/simulation-api` passed after two source-defect fixes (an `isinstance` tuple-vs-union style issue and two `Any`-typed test parameters). `mypy`, `tsc --noEmit`, and `eslint` were started; exact results are in the session's final report.
- Local-only boundary remains active: no staging, commit, push, GitHub action, Vercel link/project, preview, or production deployment.

## Sprint 12.1 — guided usability closure — 2026-07-21

- Closed all four known Sprint 12 completion defects: `/workspace?mode=advanced` now opens Advanced via a server-read, validated search parameter (`resolveInitialMode` in `apps/web/app/workspace/page.tsx`), the landing page's advanced action links there; the first-run orientation no longer touches `sessionStorage` at all (dismissal now lasts only for the mounted workspace instance, a full reload shows it again, matching the behavior already documented in `docs/USABILITY_FINDINGS.md`) and no longer risks a hydration mismatch; a new pure helper `apps/web/lib/scenario-lab/comparative-interpretation.ts` reads the existing `0.5.0` ranking order to add a factual, direction-aware "larger observed improvement" / tie / single-scenario / no-eligible-scenario statement to the Guided result summary, reusing the backend's own ranking and the centralized `1e-9` tie tolerance; Guided mode now shows one evidence panel at a time (Summary/Flow/Risk/Resources/Sensitivity/Economics/Playback/Technical) via an accessible tablist reusing the existing `RiskView`/`ResourceView`/`TechnicalView`/`SensitivityPanel`/`EconomicsPanel`/`PlaybackPanel`/`WorkflowVisualization` components with no new analytical logic; Advanced mode's full workspace (`Results` tab set plus all evidence anchor sections) is unchanged.
- Added `apps/web/tests/{comparative-interpretation,guided-evidence-navigation,workspace-orientation,workspace-mode-routing}.test.tsx` and updated four existing `workspace-scenario-lab.test.tsx` cases to exercise Advanced mode (where the full `Results` tablist now lives). `pnpm test:web` grew from 142 to 172 passing tests; no test was deleted.
- `pnpm verify` passed in full on this macOS host using Node 22.22.3 via `nvm` (root Node 20.20.0/pnpm-via-corepack is broken here with `ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING`) and the repository's existing `.venv` (Python 3.12.13): ruff, ESLint, mypy (51 files), TypeScript, 247 backend tests, 172 web tests, both builds, canonical example, all benchmark smokes, and source packaging. `/workspace` now builds as a dynamic route (expected, since it reads `searchParams`). `git diff --check` passed.
- No human participant usability testing was performed or claimed; see `docs/sprints/SPRINT_12_1_GUIDED_USABILITY_CLOSURE.md`.

## Sprint 13 — public release, case-study README, and portfolio handoff — 2026-07-21

- Documentation-only sprint: no simulation, ranking, sensitivity, economics, playback, integrity, export, or contract behavior changed. Repository remains private; no license added; no release tag created — all three explicitly owner-gated and not actioned.
- Public-safety audit found no secrets, no tracked `.env`, no temporary Vercel share-link marker, and no personal email in any tracked file; absolute local paths only appear in historical sprint/ADR documents (acceptable per this sprint's own audit rule). Stale-claim audit fixed two current-state documents: `README.md`'s "Vercel deployment is proposed, no project linked" paragraph (contradicted by the live Sprint 11 deployment) and `docs/ARCHITECTURE.md`'s "ADR-014 remains proposed" line (ADR-014 was accepted 2026-07-20). `docs/ROADMAP.md` got a short dated append for Sprints 11/12.1/13; no history was rewritten.
- Added repository governance: `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/pull_request_template.md`. Deliberately skipped `CODE_OF_CONDUCT.md` and a feature-request template as not yet justified for a solo-maintained repo.
- Captured nine production screenshots (`docs/assets/opstwin/`) via a throwaway Playwright/Chromium script (installed only in a scratch directory, no `package.json` dependency added) against `https://ops-twin.vercel.app`, plus a designed `social-preview.png` (1280×640, 104 KB). Shipped as `.png` rather than the spec's `.webp` — no local webp encoder was available (`cwebp` missing, `sips` can't encode webp on this host); disclosed in `docs/SCREENSHOT_PLAN.md`.
- **Found and did not fix (out of scope for this sprint), flagged as a follow-up task:** the Flow evidence tab's diagram/list container (`.workflow-canvas`) renders at a reproducible ~10px width in production instead of filling its available space, confirmed in two independent browser engines. No Flow screenshot was used anywhere in the public materials as a result.
- Rewrote `README.md` as a full case study (2,817 words, 22 KB, 7 embedded images, a Mermaid architecture diagram) per the required 22-section structure, including an honest usability-iteration story, the Sprint 11 deployment-incident story, and explicit limitations.
- Added `docs/PUBLIC_CLAIM_REGISTER.md`, `docs/PUBLIC_RELEASE_CHECKLIST.md` (including read-only-verified GitHub metadata recommendations via `gh repo view`/`gh api`, nothing applied), `docs/PORTFOLIO_CONTENT_PACK.md`, `docs/SCREENSHOT_PLAN.md`, and `docs/sprints/SPRINT_13_PUBLIC_PORTFOLIO_RELEASE.md`.
- Added `scripts/verify-public-release.mjs` (deterministic, network-independent) and wired `pnpm verify:public-release` into `package.json`/`scripts/tasks.mjs`'s `verify` chain only after confirming it passed standalone.
- Fixed a stale `.venv` editable install (`import app` failed despite `pip show` reporting it installed) by reinstalling with `--force-reinstall` before any test could run — recorded as environment drift, not a code defect.
- Full `pnpm verify` passed fresh on this session (not inherited from Sprint 12.1): 247 backend tests, 172 web tests (22 files), ESLint/mypy/Ruff/TypeScript clean, both builds, canonical example, all benchmark smokes, source packaging (336 files), and the new public-release verifier. `git diff --check` passed. A clean-clone check (extracting `artifacts/opstwin-source.zip` into an isolated directory and re-running bootstrap/lint/typecheck/test/build) passed identically, confirming no undocumented local state is required.
- `pnpm smoke:preview -- https://ops-twin.vercel.app` passed all eight checks; a full browser walkthrough (Guided run, Sensitivity sweep, Economics, Playback JSON export, Advanced workspace) at 390×844/768×1024/1440×900 found zero console errors and zero horizontal overflow. A handful of Next.js RSC-prefetch `?_rsc=` requests returned 404 during the walkthrough with no visible user impact (noted, not treated as a blocker).

## Sprint 15 implementation checkpoint — 2026-07-22

- Began the final beginner-comprehension repair without changing simulation,
  comparison, ranking, seed, API, or export behavior.
- Source validation confirms that `failure.probability` selects a ticket for
  quality rework and the configured failure route returns a selected ticket
  to Level 2; Guided wording now states that distinction explicitly.
- Guided presentation now leads with the fictional support problem, uses
  business-first process labels and scenario motivations, hides evidence tabs
  until a comparison completes, labels the paired relative field accurately,
  and uses direction-aware result wording with counts and percentages.
- The Process canvas now declares a full-width stretchable content/canvas
  chain, with intentional internal map scrolling above the mobile list
  fallback. Rendered width measurements are still pending browser execution.
- Node 22.22.3 direct web `tsc --noEmit` and ESLint completed cleanly.
  Vitest started but the managed runner did not return a completion summary;
  no browser QA, screenshots, deployment, commit, push, or production claim
  has been made from this checkpoint.

## Sprint 15.1 Process hotfix checkpoint — 2026-07-23

- Production browser measurement isolated the Process width defect: the
  1168 px `.workflow-section` inherited the landing page's two-column grid
  (`321.047px 650.555px`), auto-placing `.workflow-content` and the canvas
  into the 321 px first track while the internal map retained a 640 px
  minimum. The local CSS repair makes the Process section block-level and
  stacks change summary content above the map; the inspector remains beside
  the map only where its minimum width fits.
- Local Guided presentation changes add business-first Process labels and
  summaries, Advanced-only change detail, cross-scenario workload wording and
  capacity formatting, collapsed sensitivity technical evidence, dynamic
  per-minute to per-hour rate display, and playback primary-view cleanup with
  per-team full-capacity aggregation. No simulation or API behavior changed.
- Direct web ESLint, TypeScript, and `git diff --check` pass via the bundled
  Node runtime. Focused Vitest is blocked before collection: its JSDOM worker
  fails to start while reading a dependency with `ETIMEDOUT`. Rendered local
  regression, full verification, production deployment/smoke, screenshots,
  and manual desktop QA remain pending. Manual mobile QA was not performed.
