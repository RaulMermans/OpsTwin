# ADR-024: Forge Remote uses a Python adapter on the existing simulation service

- Status: accepted
- Date: 2026-11-26

## Context

CG-1 must authenticate Forge Invocation Tokens and run the existing comparison engine without duplicating simulation mathematics. Two options were evaluated:

- **A.** Dedicated FastAPI route beside the existing simulation service.
- **B.** TypeScript gateway in Next.js that verifies FIT and forwards to FastAPI.

The JavaScript FIT library in `apps/atlassian-forge` is an offline contract test, not a hosted security boundary. Introducing a second runtime only to reuse `jose` would add a hop, a second timeout, and another deployable surface.

OpsTwin Core must not take an Atlassian SDK dependency. The adapter therefore lives in `apps/simulation-api/app/integrations/`, excluded from the Core isolation scan, while public `/api/simulation/*` routes stay unauthenticated and unchanged.

## Decision

Choose option A. `POST /api/integrations/atlassian/v1/compare` verifies FIT against Atlassian JWKS, accepts only the synthetic CG-1 catalog, and calls `run_scenario_comparison`. Forge functions use `invokeRemote` from `@forge/api` with `operations: [compute]` and without app user or system tokens.

Rejected: a Node gateway; verifying FIT in the Custom UI; sending Jira issue payloads to the engine; disabling authentication on preview URLs.

## Consequences

- PyJWT and cryptography are simulation-service dependencies for FIT verification only.
- Hosted live invocation requires a Vercel deploy that includes the new rewrite, plus a Forge development deploy of the remotes block.
- CG-1 authorization is FIT + trusted app identity + synthetic-only body. Project-level authority is enforced in the Forge resolver for Jira reads and is not inferred from installation identity for operational data, because operational data is not sent.

## Validation

Python FIT and remote tests; Forge unit tests; `pnpm verify`; `pnpm verify:forge`. Live FIT remains distinct from mocked JWKS tests.
