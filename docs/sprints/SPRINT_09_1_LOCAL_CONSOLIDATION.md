# Sprint 09.1 — Local Consolidation, Packaging, and Developer Experience

## Objective

Consolidate the existing product before Sprint 10 adds representative-run playback. This sprint adds no simulation, contract, or UI-analysis capability. It packages clean deterministic source, removes manual local-development friction, reduces `workspace.tsx` to an orchestration role, hardens one economics failure path, and reconciles frontend verification status against what is actually executed.

## Independent audit findings addressed

- The uploaded source archive carried `node_modules`, virtual environments, `.next`, `.vercel` caches, build trackers, and pytest/Git internals; actual source was a small fraction of the 926 MB extracted size. This sprint adds a deterministic, size-bounded `pnpm package:source` command plus `pnpm verify:source-package`.
- Local frontend development required manually exporting `OPSTWIN_DEV_API_ORIGIN`. This sprint adds one `pnpm dev` command that starts both services with API origin configured automatically.
- `workspace.tsx` (333 lines) combined scenario/baseline form state, request lifecycle, and roughly ten result sub-views in one file. This sprint extracts the result/analysis views into dedicated components.
- The economics comparison observer used a bare `except Exception: pass`, silently discarding any unexpected evaluation failure. This sprint records safe, bounded, categorized failure evidence instead.
- Frontend test inventory (11 files, ~68 cases) is documented against actual execution status rather than assumed passing.

## Repository hygiene

Generated/machine-specific content already excluded by `.gitignore`: `node_modules/`, `.next/`, `.vercel/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `*.py[cod]`, `.env*` (except `.env.example`), `coverage/`, `dist/`, `build/`, `*.egg-info/`, `*.tsbuildinfo`. This sprint adds `artifacts/` (the source-package output directory) and confirms no forbidden path is tracked by Git (`git status` is clean; nothing under the excluded categories is staged or committed).

Local machine-specific leftovers found in the working tree during preflight (`apps/simulation-api/build`, `build-env-*`, `pytest-of-rmermans`, `.venv`, `dist/`, `.vercel/cache`, root `pip-*` directories) are already git-ignored and untouched — they are not source and are excluded by the source-package tooling below, never deleted.

## Packaging rules

`pnpm package:source` (`scripts/package-source.mjs`) builds `artifacts/opstwin-source.zip` by walking the working tree, skipping `.git` and every `.gitignore`-excluded path plus an explicit forbidden-path list (`node_modules`, `.venv`, `.next`, `.vercel`, `__pycache__`, `dist`, `build`, `*.egg-info`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `coverage`, `artifacts`, `pip-*`, `pytest-of-*`, `build-env-*`, `*.tsbuildinfo`). Files are added in sorted relative-path order with a fixed archive timestamp for determinism. A manifest (`file count`, `uncompressed bytes`, `zip bytes`, `excluded category counts`, `SHA-256`) is written to `artifacts/opstwin-source.manifest.json`. The command fails if a forbidden path is about to be archived or if the resulting ZIP exceeds 15 MB (override only by raising the constant with a documented reason in source).

`pnpm verify:source-package` (`scripts/verify-source-package.mjs`) re-opens the archive and asserts: required top-level files/directories are present (`package.json`, `apps/web`, `apps/simulation-api`, `contracts`, `docs`, `examples`), no forbidden path is present, no `.env` file other than `.env.example` is present, no secret/token-shaped filename is present, no local absolute path or username string is embedded in the manifest, and the manifest SHA-256 matches the archive bytes.

## Local development workflow

`pnpm dev` (`scripts/dev-local.mjs`) starts `apps/simulation-api` (uvicorn on `127.0.0.1:8000` by default) and `apps/web` (`next dev` on `127.0.0.1:3000` by default) as two child processes, waits for the API health endpoint, sets `OPSTWIN_DEV_API_ORIGIN` for the web child automatically, prints the Web URL, API URL, and Health URL, forwards `SIGINT`/`SIGTERM` to both children, and exits both when either child exits or the parent is terminated. Ports are configurable via `OPSTWIN_WEB_PORT` / `OPSTWIN_API_PORT` (documented defaults 3000/8000); a bound port is detected before spawning and fails clearly rather than silently retrying on another port. `pnpm dev:web` and `pnpm dev:api` remain unchanged for separate-terminal use. No Vercel command participates.

`pnpm smoke:local` (`scripts/smoke-local.mjs`) starts both services the same way `pnpm dev` does, then checks `GET /`, `GET /workspace`, `GET /api/simulation/health`, and one bounded `POST` each for `/compare/scenarios`, `/analyze/sensitivity`, and `/analyze/economics`, using same-origin relative paths through the Next.js rewrite (no CORS configuration). It shuts down both children on completion or failure.

## Frontend decomposition plan

`workspace.tsx` keeps: page-level state (baseline/scenarios/runs/objective/guardrail/health/result/error/announcement/analysisView/metricCategory), the `submit()` request lifecycle, scenario CRUD helpers, roving-tabindex analysis-view navigation, and top-level composition. Extracted into `apps/web/components/results/`: `Overview`, `MetricsView` (+ `MetricMobileCards`), `ConfidenceInterval`, `ProbabilityView`, `RiskView`, `ResourceView` (+ `ResourceValue`), `TechnicalView`, `PrintSummary`, and the shared `SummaryValue`/formatting helpers, composed by a `ResultsPanel` component that keeps the existing `Results` contract (same props: `result`, `analysisView`, `metricCategory`, scenario/baseline context). No route, CSS class, accessibility attribute, request payload, or scenario-ID behavior changes. `SensitivityPanel`/`EconomicsPanel`/`WorkflowVisualization` were already extracted in earlier sprints and are unchanged.

## Error-observability policy

Economic comparison's per-run observer (`apps/simulation-api/app/economics/comparison.py`) now catches evaluation exceptions, logs a warning with the safe exception type name (never the raw message, path, or traceback), and appends an `EconomicObserverFailure` (`variantId`, `runIndex`, `errorCategory: "economic_snapshot_failure"`, a fixed safe `message`) to `EconomicExecutionMetadata.observerFailures` (contract `0.7.0`, additive field, default empty list). Operational comparison is never affected — evaluation failures only remove that run/scenario from economic pairing, exactly as before, but the failure is no longer silently invisible. A focused test (`test_observer_failure_is_isolated_and_recorded`) injects a synthetic failure on one scenario run and asserts the operational comparison stays valid, exactly one categorized failure is recorded, and the message contains no path or exception-detail leakage.

## Test execution status

See `docs/VALIDATION_PLAN.md` frontend inventory addendum and the Sprint 09.1 verification gate below for exact executed/blocked status. Vitest cases are never reported as passed unless actually executed and observed passing in this session.

## In scope

Source packaging and verification, one-command local dev + smoke, `workspace.tsx` decomposition, economics observer hardening, frontend/backend verification-status reconciliation, `.gitignore`/doc hygiene.

## Out of scope

Any new simulation, contract, or analysis capability; any UI feature; any deployment, Git, or GitHub action; representative-run playback (Sprint 10).

## Acceptance criteria

Matches CLAUDE.md section 20 (source packaging deterministic and under threshold; `pnpm dev` is the standard local workflow with automatic API origin; `workspace.tsx` reduced to orchestration; behavior unchanged; economics failures isolated and observable; frontend verification status accurate; available targeted checks pass; no Git/deployment action).

## Definition of done

Packaging, dev orchestration, decomposition, and observer hardening are implemented and exercised by targeted local checks; `SCRATCHPAD.md` and the docs listed in CLAUDE.md section 11 are updated; verification status (executed/blocked) is reported honestly in the final session report.

## Rollback plan

If `pnpm dev` destabilizes existing workflows, remove `scripts/dev-local.mjs`/the `dev` task and keep `dev:web`/`dev:api`. If the `workspace.tsx` decomposition regresses behavior, reinstate the previous inline render functions from version control one extraction at a time rather than redesigning the page. If the economics observer change causes an unexpected serialization failure, revert `EconomicObserverFailure`/`observerFailures` and the corresponding schema addition together (they are additive and isolated from every other 0.7.0 field).
