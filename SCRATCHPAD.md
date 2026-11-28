# OpsTwin Scratchpad

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
