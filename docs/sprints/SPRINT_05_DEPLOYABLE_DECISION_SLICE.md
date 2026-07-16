# Sprint 05 — Deployable Decision Slice

## Objective

Deliver one complete support-operations journey from understandable assumptions through a real paired comparison, and validate the Next.js and FastAPI services behind one same-origin Vercel Services boundary.

## User outcome

An operations or business user can review the incoming-ticket workflow, edit eight bounded assumptions, create up to three guided scenarios, select an objective and 10–100 runs, execute the existing `0.5.0` comparison, and interpret factual ranking, delta, risk, guardrail, and integrity evidence without editing JSON.

## In scope

- Canonical support product fixture and two-scenario request.
- Stable `/api/simulation` routes and safe public error envelopes.
- Landing and single-route workspace.
- Baseline, demand/staffing/process/quality scenario controls, settings, loading/cancel, results, and technical disclosure.
- Narrow runtime-checked TypeScript client using relative same-origin paths.
- Vercel Services configuration, local routing, preview attempt when authenticated, payload guards, frontend tests, browser QA, and GM-042–GM-052.

## Out of scope

Persistence, accounts, authentication, arbitrary model editing, topology changes, charts, recommendations, costs, sensitivity analysis, background work, parallel simulation, multiple industries, and production promotion.

## Product safety limits

- UI scenarios: maximum 3.
- Run choices: 10, 25, 50, 100.
- UI work guard: 30,000 item executions.
- Backend work guard remains 100,000.
- Browser evidence: sampled representatives only, never full.
- Canonical response guard: 1,000,000 uncompressed JSON bytes.

## Acceptance

The backend remains reproducible and green; mapped fixtures and errors validate; the UI is accessible and responsive; all mathematics remain server-owned; same-origin Services routing passes locally; a preview is measured only when authenticated; and the repository passes all gates without a production deployment, commit, or push.

## Rollback

If backend behavior changes, stop UI work and restore the prefixed API boundary to the last 192-test state. If Services routing fails, retain separate local web/API commands and fix configuration before touching simulation code. Never add an external backend or persistence as a shortcut.
