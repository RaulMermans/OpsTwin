# Atlassian integration architecture

## Boundaries

```text
JSM project (OPS)
  -> Forge Custom UI (apps/atlassian-forge/static/transformation-lab)
  -> Forge resolver (user context, project key from extension context)
  -> [CG-2] asUser Jira/JSM ingest -> operational snapshot os.1.0.0 (session)
  -> [CG-1] Forge Remote + FIT validation (synthetic catalog only)
  -> OpsTwin simulation service (existing 0.5.0/0.7.0 contracts)
```

Core FastAPI routes stay unchanged in CG-0. Do not send OAuth tokens or raw issue descriptions to the simulation service.

## Why Forge Remote

Official Forge Remote (retrieved 2026-11-26, https://developer.atlassian.com/platform/forge/remote/):

- FIT in `Authorization: Bearer` validated against Atlassian JWKS
- UI module timeout 25s; events 5s
- Optional `x-forge-oauth-user` / `x-forge-oauth-system` must be treated as opaque and never logged
- Using Remote **makes the app ineligible for Runs on Atlassian**

The existing comparison path is Python/SimPy. Duplicating it on Forge Node would violate ADR-002 and ADR-023.

## CG-0 implemented

- Registered Forge manifest, Custom UI, read-only resolver
- Local FIT contract tests (`64 KiB` bound)

## CG-1 remote

Hosted path (ADR-024): `POST /api/integrations/atlassian/v1/compare` on the existing FastAPI service. FIT is required. Public `/api/simulation/*` is unchanged. CG-1 bodies are synthetic catalog inputs only; Jira issue text is never forwarded.

Sources retrieved 2026-11-26: [Forge Remote](https://developer.atlassian.com/platform/forge/remote/), [essentials](https://developer.atlassian.com/platform/forge/remote/essentials/) (UI timeout 25s), [remotes](https://developer.atlassian.com/platform/forge/manifest-reference/remotes/), [endpoint](https://developer.atlassian.com/platform/forge/manifest-reference/endpoint/), [invokeRemote](https://developer.atlassian.com/platform/forge/apis-reference/ui-api-bridge/invokeRemote/).
