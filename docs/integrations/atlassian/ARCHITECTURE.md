# Atlassian integration architecture

## Boundaries

```text
JSM project (OPS)
  -> Forge Custom UI (apps/atlassian-forge/static/transformation-lab)
  -> Forge resolver (user context, project key from extension context)
  -> [CG-1] Forge Remote + FIT validation
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

- Unregistered Forge manifest, Custom UI, read-only resolver
- Local FIT verifier and payload bound (`64 KiB`) with unit tests
- No `remotes:` block, because no internet-reachable authenticated development endpoint is authorized yet

## CG-1 required remote

1. Owner registers a distinct OpsTwin Forge app (not RE:VERSE).
2. Host a development-only Remote that verifies FIT (`iss=forge/invocation-token`, `aud` and `app.id` = trusted app ARI, expiry, installation ARI).
3. Map synthetic or normalized operational models to existing comparison requests.
4. Keep production `https://ops-twin.vercel.app/api/simulation/*` free of Forge auth unless a separate isolated route is explicitly approved.
