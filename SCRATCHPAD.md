# OpsTwin Scratchpad

## Codegeist CG-7.1 — reconstruct fix 2026-11-28

- Jira/CSV transform failed after FIT accept: compact reconstruction dumps `exclude_none`, diagnostic `ParameterEstimate.value` is null, reconstruct raised uncaught `ValidationError`. Same fingerprint as live Jira exploratory model (`2a5324ff72a5a001…`). Manual path reconstructs from spec, so it worked.
- Fix: `value` defaults to `None`; transform catches reconstruct `ValidationError` as 422; Forge transform/economics resolvers wrap uncaught errors; Custom UI execution selects include 80×8. Resolver `timeoutSeconds` is invalid for queue/project pages — not used.
- Local: `test_csv_baseline_token_completes_remote_transform` 200 complete; `test_cg7_byod.py` 15 passed; Forge 98 tests + UI build.
- Hosted: production `dpl_4PYB627CiNLCVPgTHhwDNC7yr32E` aliased to `https://ops-twin.vercel.app`. `GET /api/simulation/health` 200. Unauth transform 401 `FIT_INVALID`. HMAC unchanged. Forge development **3.11.0**. Live Custom UI click of Jira transform not re-captured (iframe). Not pushed.
- GitHub `origin/master` remains PR #13 `6ed94d1`. CG-8 not started.

## Codegeist CG-7.1 live acceptance — 2026-11-28 (final)

- Branch `feat/codegeist-cg7.1-release-blockers`. Local HEAD will move past `515711e` with fail-closed project GET + non-synthetic economics fixture omission. Do not treat browser `sourceMode` as permission. Project GET ≠ issue-level access (`docs/integrations/atlassian/SECURITY.md`).
- GitHub `origin/master` is PR #13 `6ed94d1` (includes `515711e`). Not pushed from this working tree until authorized.
- Production alias: `dpl_68NFGnTRqs5sL2QgT4J11DpDErWV` → `https://ops-twin.vercel.app`. Previous RC `dpl_Fg2pyDcFU7KUBVr4P6VnAFZ1Wb39` READY. HMAC unchanged. Health 200. Unauth construct 401 `FIT_INVALID`.
- Forge CLI major 3, install `b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815` Up-to-date. Sprint notes 3.9.0 vs docs commit 3.8.0: 3.9.0 is the compact-`experimentId` deploy.
- OPS lab: five `[OpsTwin synthetic]` Get IT help issues. Import 5 cases, window `2026-10-29T09:10:24.437Z → 2026-11-28T09:10:24.437Z`, request types unclassified, lifecycle_coverage fail (no status-change histories), authorization_coverage pass. Exploratory Jira model `2a5324ff72a5a001bdd61a4cd03f04d514f7d2f89189ffbd18190720895e193b`, validation `empty_system_generative`.
- Jira multi-scenario invoke: Forge unexpected error after FIT accept (`transform` 09:15:33Z). Not presented as a completed Jira experiment.
- Manual 800/30d/1+1/12+40/p=0.9: fingerprint `07f6095ebf9acbd88fe73b65201e4d932f4628d77b064ea7363423301f7d451c`. 40×5 human+hybrid: cycle 319.044 / 122.289 / hybrid 200.588, integrity passed. Economics blocked on synthetic fixture identity until Forge upgrade of this commit.
- CSV template: fingerprint `e9f56ad46b00292041fb18216f8d105b25a030c5101d708fe837ac0148f91116`, validation failed (`empty_system_generative`). Not an empirically validated forecast.
- `pnpm verify:forge` 97 tests + UI build. `pnpm verify` not re-run (no Core/Python edits). CG-8 not started.

## Codegeist CG-7.1 checkpoint — 2026-11-28

- Branch `feat/codegeist-cg7.1-release-blockers`. RC commit `6d3b82a`. Not pushed. Rollback git `checkpoint/cg7.1-start` (`5f9d98b`).
- Snapshot continuity: construct re-extracts using the reviewed observation window. Clock drift no longer invalidates an unchanged cohort. Material source change returns `review_required` without replacing the reviewed fingerprint.
- Auth: no shared `scope:installation-user-context` fallback. Missing principal fails closed. FIT principal must match when present. Jira source access is rechecked before construct/transform/economics. Signed `sourceMode` must match the request. Jira-hosted synthetic origin stays synthetic on the artifact and token.
- Local BYOD: synthetic + manual + CSV each completed transform and economics. CSV stays enabled.
- Hosted: preview `dpl_GyjpyQVqHdMjrvzL7b9sn2cVP7RB`. Production `dpl_Fg2pyDcFU7KUBVr4P6VnAFZ1Wb39` aliased to `https://ops-twin.vercel.app`. HMAC secret preserved. Homepage 200, health 200, unauth construct 401 `FIT_INVALID`, public simulate integrity passed (16). Previous production rollback: `dpl_BsEjmQGguZYQSbdtR5FMjh7aXqJh`.
- Forge development **3.9.0** deployed (compact `experimentId`); OPS install `b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815`. No Forge production / Marketplace.
- Playwright (iframe `contentFrame`, signed in as raulmermans@gmail.com) on OPS lab 2026-11-28:
  - Synthetic FIT path already complete (20×2 integrity passed; hybrid economics ROI withheld).
  - Jira import 30d and 90d: **valid empty dataset**, 0 cases, `authorization_coverage: pass`, calibration refused. Window 90d `2026-08-30T08:03:28.791Z → 2026-11-28T08:03:28.791Z`. Not a malformed empty. Continuity fingerprint reuse **not exercised** (no live tickets).
  - Manual exploratory 800/30d, 1+1, 12/40, p=0.9: constructed, hybrid yes, fingerprint `07f6095ebf9acbd88fe73b65201e4d932f4628d77b064ea7363423301f7d451c`.
  - CSV template validate + mapping review + source-linked construct: model fingerprint `e9f56ad46b00292041fb18216f8d105b25a030c5101d708fe837ac0148f91116`, historical validation **failed** (`empty_system_generative`).
  - Malformed CSV: alert `Row 2 has an invalid UTC timestamp.`
  - Correlation IDs not shown in the Custom UI. Forge invokes are GraphQL `useInvokeExtensionRelayMutation` only.
- `pnpm verify` 352 pytest; `pnpm verify:forge` 94 tests. CG-8 not started.

## Codegeist CG-7 checkpoint — 2026-11-27

- Branch `feat/codegeist-cg7-byod-production-hardening` from CG-6 `1784a20`. Recoverable `checkpoint/cg7-start`. Working tree uncommitted. Not pushed.
- Hosted production `dpl_BsEjmQGguZYQSbdtR5FMjh7aXqJh` → `https://ops-twin.vercel.app`: health 200, unauth construct-baseline/transform 401 `FIT_INVALID` (no Vercel 403). Preview `dpl_4ttGhk4RNV97oiYFxYU2rcAkwfYc`.
- HMAC secret present on Vercel production. Forge development **3.7.0**, install `b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815`.
- Manual/Jira/CSV baselines share Core calibration + comparison. Economics uses evaluation_basis + signed tokens. Break-even requires `strategyId`.
- Local 20×2 seed 20261127: synthetic cycle 17.490/17.490/16.843/16.371; manualA 10.328 vs manualB 200.823 (distinct fingerprints). Golden recurring ROI 14.
- Live Jira Custom UI journeys not clicked (cross-origin iframe). Second site not installed. Historical calibration not claimed.
- `pnpm verify` and `pnpm verify:forge` passed. CG-8 not started.

## Codegeist CG-6 checkpoint — 2026-11-27

- Branch `feat/codegeist-cg6-economic-decision-intelligence` from CG-5 `6a2f0f2`. Recoverable `checkpoint/cg6-start`. Not pushed.
- Decision overlay `cg6.v1` reuses calendar payroll + explicit realization; not a second engine. ADR-029. Native **Investment Decision** workspace.
- Measurement: fixed workload until empty. Completions comparable; throughput/utilization not cash denominators.
- Hosted: production deploy `dpl_GHxMygNfRXUrCosM8Q8AAcjFNhvK` aliased to `https://ops-twin.vercel.app`. Preview `dpl_F6zUeat3KYfRMNheCneFrbw1SL7h`.
- Agent curl to production now hits Vercel Security Checkpoint (403 HTML). FIT 401 not re-observed from this agent after the promote.
- Forge development **3.6.0** deployed. Live Jira click of the economic journey not completed (iframe + checkpoint).
- Local: `pnpm verify` and `pnpm verify:forge` passed (88 Forge tests). Golden ROI/payback/break-even tests in `test_economic_decision.py`.
- Live operational calibration still not claimed.

## Codegeist CG-5 checkpoint — 2026-11-27

- Branch `feat/codegeist-cg5-native-product-experience` from CG-4 `b825838`. Recoverable `checkpoint/cg5-start`. Not pushed.
- Native IA: Overview / Operational Data / Baseline Model / Transformation Lab / Results. `cg5.v1` multi-alternative transform over existing comparison. Fixture `cg5-hybrid-support`. ADR-028.
- Hosted production `https://ops-twin.vercel.app` deploy `dpl_gKxbD7Qr2UpwxkghscYAu7vozYDL`: health 200; unauthenticated transform 401 `FIT_INVALID`; standalone 200.
- Forge development **3.5.0**, install `b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815`.
- Local 20×5 hybrid-capable experiment: cycle 17.610 / 17.610 / 16.707 / 14.139; extra staff no cycle change under zero wait; hybrid CI excludes 0. Exploratory constructed model.
- `pnpm verify`: 329 pytest. `pnpm verify:forge`: 85 tests + UI build.
- Live Jira click of CG-5 not completed (no Atlassian session in agent browser). Live operational calibration still not claimed.
