---
name: verify-local-consolidation
description: Verify OpsTwin Sprint 09.1 source packaging, one-command local development, workspace decomposition, and economics observer hardening without any Git or deployment action.
---

# Verify local consolidation

1. Read `docs/sprints/SPRINT_09_1_LOCAL_CONSOLIDATION.md`.
2. Run `node scripts/package-source.mjs` then `node scripts/verify-source-package.mjs`. Confirm: no `node_modules`, `.venv`, `.next`, `.vercel`, `.git`, `dist`, `build`, `.egg-info`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `pip-*`, `pytest-of-*`, or `build-env-*` path is archived; the manifest SHA-256 matches the archive; required source files are present; and the archive is under 15 MB.
3. Inspect `scripts/dev-local.mjs` and `scripts/smoke-local.mjs`: confirm both spawn `apps/simulation-api` (uvicorn) and the `next` binary directly (not through `pnpm`), set `OPSTWIN_DEV_API_ORIGIN` automatically, detect port conflicts before spawning, and forward `SIGINT`/`SIGTERM` to both children.
4. Inspect `apps/web/app/workspace/workspace.tsx`: confirm it stays orchestration-only (state, request lifecycle, scenario CRUD, top-level composition) and that `apps/web/components/results/results-panel.tsx` and `apps/web/lib/scenario-lab/scenario-labels.ts` hold the extracted result-view rendering and scenario-label data with no behavior, route, CSS class, or request-payload change.
5. Inspect `apps/simulation-api/app/economics/comparison.py`: confirm the observer no longer has a bare `except Exception: pass`, records a bounded `EconomicObserverFailure` (`variantId`, `runIndex`, `errorCategory`, a fixed safe `message` with no path/traceback text), and that operational comparison still returns successfully when one economic evaluation fails. Confirm `contracts/economic-comparison-result.schema.json` was updated to match the new `observerFailures` field.
6. Run available targeted checks (`tsc --noEmit`, `eslint`, `pytest tests/test_economic_comparison.py`, focused Python tests) directly via the local binaries if the `pnpm`/corepack wrapper is broken in the current environment. Report exact executed/blocked status per command; never report static inspection as a passing runtime check.
7. Confirm no `git add`, commit, push, remote, GitHub, or Vercel action occurred (`git status` must show only the expected working-tree changes).
