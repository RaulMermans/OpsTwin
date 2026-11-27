# OpsTwin Scratchpad

## Codegeist CG-5 checkpoint — 2026-11-27

- Branch `feat/codegeist-cg5-native-product-experience` from CG-4 `b825838`. Recoverable `checkpoint/cg5-start`. Not pushed.
- Native IA: Overview / Operational Data / Baseline Model / Transformation Lab / Results. `cg5.v1` multi-alternative transform over existing comparison. Fixture `cg5-hybrid-support`. ADR-028.
- Hosted production `https://ops-twin.vercel.app` deploy `dpl_gKxbD7Qr2UpwxkghscYAu7vozYDL`: health 200; unauthenticated transform 401 `FIT_INVALID`; standalone 200.
- Forge development **3.5.0**, install `b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815`.
- Local 20×5 hybrid-capable experiment: cycle 17.610 / 17.610 / 16.707 / 14.139; extra staff no cycle change under zero wait; hybrid CI excludes 0. Exploratory constructed model.
- `pnpm verify`: 329 pytest. `pnpm verify:forge`: 85 tests + UI build.
- Live Jira click of CG-5 not completed (no Atlassian session in agent browser). Live operational calibration still not claimed.

## Codegeist CG-4 checkpoint — 2026-11-27

- Branch `feat/codegeist-cg4-ai-interventions` from `checkpoint/cg3.1-complete` (`482675b`). See `docs/codegeist/sprints/CG-04.md` for live evidence.
- Adapters in `app/interventions/`; remote `POST /api/integrations/atlassian/v1/transform`; Experiments UI. ADR-027.
- Hosted production `https://ops-twin.vercel.app` deploy `dpl_5cTJgujgEgUKGGZ2mBss6ahvn8XU`: health 200; unauthenticated transform 401 `FIT_INVALID` (no longer 404).
- Forge development **3.4.0** on `opstwin-dev.atlassian.net` / install `b1bb872d-...` (list shows major 3, Up-to-date).
- Local: 326 pytest, 81 Forge tests.
- Live Jira 2026-11-27: OPS queue page, CG-4 lab. Golden fixture + approved lab assumptions → `validated_for_defined_scope`, constructed fingerprint `32206b92…`, holdout `passed_for_defined_scope` (empty-system generative). Capacity still assumption-bound (4). Experiments: human capacity +1/+1, 40 items × 5 paired runs, comparative evidence + disclosures returned. Synthetic fixtures only; not this project's history.
- Live operational calibration still not claimed.
