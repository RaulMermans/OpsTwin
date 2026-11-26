# Security (Atlassian layer)

## Rules

- Never commit API tokens, OAuth headers, FIT values, or `.env` files.
- Owner runs `forge login` in their own terminal. Tokens are not pasted into chat.
- Resolvers use **user context** (`api.asUser()`) and the Forge **extension project key**, not client-supplied IDs.
- Display conditions are not authorization.
- Do not log Authorization headers or JWTs (`sanitizeRemoteLog`).
- Payload cap for future Remote: 64 KiB.
- Placeholder app ARI `.../00000000-0000-4000-8000-000000000000` must not accept Remote traffic.

## CG-0 tests

`apps/atlassian-forge/src/remote/fit.test.js` covers missing auth, invalid token, expiry, wrong audience, wrong app id, unregistered identity, and oversized bodies.

Live FIT against Atlassian JWKS is **not** verified this sprint.

## Data residency

Forge Remote plus an external Python host is extra responsibility under the Forge shared-responsibility model. Isolated Cloud requires `icLabel`-specific JWKS URLs. Production residency pinning is deferred past CG-0.

## Runs on Atlassian

Remote compute is intentionally out of that bonus program. See `docs/codegeist/ELIGIBILITY.md`.
