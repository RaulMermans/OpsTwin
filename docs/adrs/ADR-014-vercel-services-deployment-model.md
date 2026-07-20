# ADR-014: Vercel Services deployment model

- Status: accepted (2026-07-20)

## Context

OpsTwin is a polyglot Next.js/FastAPI repository. Both services must deploy together behind one public domain. Current Vercel Services replaces the earlier experimental configuration for new projects, and same-origin routing must preserve the public API path.

## Options considered

### Option A — Current Vercel Services model

Two services, one project, top-level public rewrites.

### Option B — Legacy experimental Services model

Uses obsolete `experimentalServices` configuration.

### Option C — Separate Vercel projects

Separates deployment lifecycle and public boundaries.

### Option D — Vercel frontend and external Python host

Adds another platform and cross-origin boundary.

## Decision

Choose Option A: deploy Next.js and FastAPI as two services in one Vercel project using `services` and top-level rewrites.

## Consequences

- Root `vercel.json` owns public routing.
- Services retain separate dependency roots.
- FastAPI implements the original `/api/simulation/**` path received after routing.
- Execution remains stateless.
- Services remains a beta capability and requires preview validation.

## Revisit triggers

Incompatible Services changes, representative workloads exceeding function limits, a requirement for durable asynchronous execution, or a platform change that materially reduces complexity.

## Validation plan

Run `vercel dev -L`, `vercel build` where linkage permits, preview deployment, same-origin browser flow, preview API replay, and runtime/payload evidence. Mark accepted only after successful preview validation; otherwise record the exact blocker and retain proposed status.

## Acceptance evidence (2026-07-20)

Sprint 11 fixed a packaging defect that broke the `web` service's Turbopack build (see `docs/sprints/SPRINT_11_RUNTIME_AND_FLAGSHIP_POLISH.md`) and then completed one full production deployment of the existing `ops-twin` Vercel project: one project, two services (`web`/Next.js 16.2.10, `simulation`/FastAPI on `python3.12`), one production domain (`https://ops-twin.vercel.app`), routed by the unchanged root `vercel.json` rewrites. `/`, `/workspace`, `/api/simulation/health`, and all six analysis routes (`simulate`, `simulate/repeated`, `compare/scenarios`, `analyze/sensitivity`, `analyze/economics`, `analyze/economic-sensitivity`) returned correct evidence with passing integrity at bounded run counts (10, 25, and the existing 50-run canonical fixture). `pnpm smoke:preview -- https://ops-twin.vercel.app` passed in full. A live browser session exercised the complete product journey (landing → workspace → comparison → Overview/Metrics/Risk/Resources/Technical → Flow → Sensitivity → Economics → Playback → JSON/CSV export) with zero console errors, zero failed network requests, and no `localhost` reference. Full evidence, including timings and response sizes, is recorded in `docs/VERCEL_PREVIEW_EVIDENCE.md`.
