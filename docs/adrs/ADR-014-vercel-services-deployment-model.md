# ADR-014: Vercel Services deployment model

- Status: proposed

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
