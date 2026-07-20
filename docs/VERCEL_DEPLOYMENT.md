# Vercel Services Deployment

## Architecture

One Vercel project contains a Next.js service rooted at `apps/web` and a FastAPI service rooted at `apps/simulation-api`. Root `vercel.json` owns ordered public rewrites. `/api/simulation/(.*)` routes to FastAPI and `/(.*)` routes to Next.js. Services preserves the original public path, so FastAPI defines the complete `/api/simulation` prefix.

This uses the current `services` model described in Vercel's June 2026 Services guidance, not the legacy `experimentalServices` model: <https://vercel.com/kb/guide/vercel-services>.

## Entrypoint and dependencies

The simulation service entrypoint is `app.main:app`, declared by the service and `[tool.vercel]` only where current local validation confirms no conflict. Runtime dependencies stay in `apps/simulation-api/pyproject.toml`; the service is stateless and does not write durable files.

## Commands

- `pnpm dev:vercel`: `vercel dev -L` for the complete local router.
- `pnpm build:vercel`: local Vercel build where CLI linkage permits it.
- `pnpm smoke:vercel-local`: checks the local router's web, health, single, repeated, comparison, validation, and work-limit paths.
- `pnpm smoke:preview -- <url>` or `VERCEL_PREVIEW_URL=<url>`: same checks against an explicit preview URL.

Separate fallback development remains `pnpm dev:web` plus `pnpm dev:api`. The standard local development path is `pnpm dev` (`scripts/dev-local.mjs`), which starts both services directly (no Vercel CLI involvement) with `OPSTWIN_DEV_API_ORIGIN` configured automatically; it is unrelated to `pnpm dev:vercel` and does not link or require a Vercel project.

## Current constraints

- Function request and response bodies have a documented 4.5 MB limit. The product applies a conservative 1 MB uncompressed comparison-response guard: <https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions>.
- FastAPI is packaged as one Python function. Current Python guidance documents a 500 MB uncompressed bundle limit; OpsTwin does not opt into Large Functions: <https://vercel.com/docs/frameworks/backend/fastapi>.
- Maximum duration depends on the active Vercel plan/runtime configuration and must be verified from the linked preview; no duration field is guessed in source.
- The backend work guard remains 100,000; the UI stops above 30,000 until preview evidence supports reconsideration.
- No persistent writable filesystem, background worker, cross-origin API, or secret is required.

## Deployment status (2026-07-20)

The `ops-twin` Vercel project (Services model, two services) is deployed to production at `https://ops-twin.vercel.app`, built from `origin/master`. ADR-014 is accepted; GM-051 passes. See `docs/VERCEL_PREVIEW_EVIDENCE.md` for the full evidence record (routes, smoke, browser QA, timings, payload sizes) and `docs/sprints/SPRINT_11_RUNTIME_AND_FLAGSHIP_POLISH.md` for the sprint narrative.

Sprint 11 fixed one packaging defect before this deployment succeeded: `apps/web/lib/templates/support.ts` imported `../../../../examples/product/support-operations-baseline.json`, a path `.vercelignore` excludes from the deployed bundle, so Turbopack failed with "Module not found" in production. `apps/web` now owns a runtime copy of that JSON directly (`apps/web/lib/templates/support-operations-baseline.json`), and `pnpm verify:vercel-runtime` (wired into `build:vercel` and `verify`) checks the two files stay semantically identical and that `support.ts` never re-imports the ignored `examples/` path.

Configuration that made this deployment possible:

- `vercel.json` (Services model, two services, ordered public rewrites) and `apps/simulation-api/pyproject.toml`'s `[tool.vercel]` entrypoint remain consistent with each other.
- `apps/web/next.config.ts`'s development-only API rewrite is gated on `OPSTWIN_DEV_API_ORIGIN`, which is never set in a Vercel build; in production, routing is owned entirely by the root `vercel.json` rewrites, not by Next.js.
- A root `.vercelignore` excludes `docs/`, `examples/`, `.claude/`, `.agents/`, `scripts/`, `artifacts/`, and both services' `tests/` directories from the deployed bundle (dev tooling only; the web runtime baseline JSON lives inside `apps/web` precisely so it survives this exclusion).
- Work added in Sprint 09.1/10 (packaging/dev-orchestration scripts, the workspace decomposition, the economics observer hardening, and the representative-playback feature) introduced no new environment variable, no new backend route, and no change to `vercel.json`; none of it affected deployability once the packaging defect above was fixed.

## Preview procedure

1. Run `vercel --version` and `vercel whoami`.
2. If authenticated, link/create only the preview project as needed; keep `.vercel/` ignored.
3. Run `pnpm build:vercel`, then `vercel` without `--prod`.
4. Run preview smoke and browser checks against the emitted URL.
5. Record cold/warm timings, bytes, hashes, errors, console, versions, and source state in `VERCEL_PREVIEW_EVIDENCE.md`.

No production promotion occurs in this sprint.

## Smoke and rollback

Smoke checks cover `/`, `/workspace`, health, single, repeated, comparison, validation, and work limit. A failed preview may be ignored or removed in Vercel; inspect CLI/runtime logs, revert `vercel.json`/entrypoint changes in Git, and return to separate local servers. Future production promotion would require a separately authorized `vercel --prod` after preview acceptance.

## Known limitations

Services is a current beta capability and project framework selection must be Services. Local timing is not hosting evidence. Browser abort stops waiting for a response but does not claim server-side cancellation.
