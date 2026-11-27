# Security (Atlassian layer)

## Rules

- Never commit API tokens, OAuth headers, FIT values, or `.env` files.
- Owner runs `forge login` in their own terminal. Tokens are not pasted into chat.
- Resolvers use **user context** (`api.asUser()`) and the Forge **extension project key**, not client-supplied IDs.
- Operational snapshots stay in the Forge resolver/UI session. They are not posted to the simulation remote.
- Assignees are stored as `ref_` plus a truncated SHA-256 of `accountId`. Descriptions, comments, attachments, and emails are not requested.
- Display conditions are not authorization.
- Do not log Authorization headers or JWTs (`sanitizeRemoteLog`).
- Payload cap for future Remote: 64 KiB.
- Placeholder app ARI `.../00000000-0000-4000-8000-000000000000` must not accept Remote traffic.

## CG-1 tests

Offline FIT tests (JS contract + Python production verifier) cover missing auth, malformed bearer, missing/expired `exp`, `nbf`, issuer, audience, app id, installation ARI, environment, unsupported algorithms, untrusted keys, oversized bodies, and log redaction.

Live FIT against Atlassian JWKS is a separate gate from those mocked-key tests. Unauthenticated `POST /api/integrations/atlassian/v1/compare` must return 401.

## Dependency advisories (CG-1)

Inspected 2026-11-26 with `npm audit` (no `--force`):

- `@forge/api` → `@forge/manifest` → `glob`/`minimatch` (moderate). Suggested fix installs `@forge/api@6.1.1` (breaking). Left unresolved.
- `@forge/bridge` → `@atlaskit/adf-schema` → `prosemirror-view` XSS GHSA-c8x8-7fp4-3x9w (high). Suggested fix installs `@forge/bridge@5.5.0` (breaking, older). Custom UI uses `invoke`/`view` only; paste handling is not used. Left unresolved.

## Data residency

Forge Remote plus an external Python host is extra responsibility under the Forge shared-responsibility model. Isolated Cloud requires `icLabel`-specific JWKS URLs. Production residency pinning is deferred past CG-0.

## Runs on Atlassian

Remote compute is intentionally out of that bonus program. See `docs/codegeist/ELIGIBILITY.md`.
