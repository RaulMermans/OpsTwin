# ADR-005: Single Vercel project deployment

- Status: accepted

## Context

OpsTwin contains a TypeScript frontend and a Python simulation service. The product should remain simple to deploy and demonstrate, while multiple external platforms would add unnecessary operational complexity. Simulation logic must remain stateless and compatible with bounded function execution.

## Options considered

### Option A — One Vercel project

Deploy the Next.js interface and bounded Python simulation API/functions behind one public project boundary.

### Option B — Vercel frontend and Railway simulation API

Split the public application across two deployment platforms.

### Option C — Entire application on Railway

Deploy both frontend and Python service on Railway.

## Decision

Deploy the Next.js interface and Python simulation API within one Vercel project and one public deployment boundary. Deployment configuration is deferred.

## Rationale

One project minimizes operational surface while preserving internal TypeScript/Python boundaries and a straightforward demonstration path.

## Consequences

- The Python simulation service must remain stateless.
- Local filesystem persistence cannot be assumed.
- Long-running simulations may later require chunking, persistence, or another Vercel-compatible execution pattern.
- Frontend and Python code retain clear internal boundaries.
- No deployment configuration is added in this sprint.

## Revisit triggers

- Simulation duration cannot fit suitable Vercel execution limits.
- Workloads require continuously running workers.
- Monte Carlo execution requires durable asynchronous orchestration.
- Infrastructure cost or operational constraints materially favor another architecture.

## Validation plan

Deploy a small frontend-to-Python request in a later deployment sprint and measure realistic simulation execution time before adding job infrastructure.

## 2026-07-16 validation note

Sprint 05 adopts the current Vercel Services `services` model with two roots and top-level same-origin rewrites, as proposed in ADR-014. ADR-005's one-project decision remains unchanged. ADR-014 remains proposed until an actual Services preview validates routing and runtime limits.
