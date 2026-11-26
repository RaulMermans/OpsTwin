# ADR-023: Atlassian application isolation

- Status: accepted
- Date: 2026-11-26

## Context

OpsTwin is an independent simulation product. Codegeist 2026 requires a Forge app that integrates with at least one Atlassian product. Converting the whole repository into a Forge app would couple simulation mathematics to Atlassian runtime, credentials, and marketplace distribution.

## Decision

Keep three layers:

1. **OpsTwin Core** — `apps/simulation-api`, `apps/web`, `contracts/`. Platform-independent.
2. **Integration contracts** — documented in `docs/integrations/atlassian/DATA_CONTRACT.md`. No Atlassian types leak into Core.
3. **Atlassian application** — `apps/atlassian-forge/`. Forge manifest, Custom UI, resolvers, and future Forge Remote adapter.

Dependency direction is Atlassian application → contracts → Core. Core must never import Forge or Atlassian modules.

## Options considered

Monorepo Forge conversion; separate GitHub repository; iframe the existing Vercel app from Jira.

A separate repository would split verification. Iframing production would send tenant context to an unauthenticated public API.

## Consequences

- `pnpm verify` continues to prove the standalone product.
- `pnpm verify:forge` proves the isolated Forge foundation.
- Forge Remote is required for simulation execution inside Jira; that path is ineligible for the **Runs on Atlassian** bonus even if it remains eligible for the main Codegeist categories.
- No change to public simulation routes on `https://ops-twin.vercel.app` in CG-0.

## Revisit triggers

Forge Remote timeouts or payload limits make Core comparison requests impossible without a bounded Core contract change; Marketplace packaging requires a different distribution boundary.

## Validation plan

`scripts/verify-atlassian-isolation.mjs` and `apps/atlassian-forge` unit tests. Live `forge create` / deploy remain blocked until owner authentication.
