# OpsTwin Scratchpad

## Codegeist CG-7.1 checkpoint — 2026-11-27

- Branch `feat/codegeist-cg7.1-release-blockers` from CG-7 `5f9d98b`. Tag `checkpoint/cg7.1-start`. Not pushed. Commit not created until owner asks.
- CSV template validates as `os.1.0.0` (partial completeness). Browser Jira snapshots rejected. Tokens bind project/principal/purpose. Mapping editor added.
- Realistic golden: released 1200 h, cash 12000, investment 8000, net 4000, ROI 0.5. Implausible 72000-min busy withholds cash.
- Demo 80×8 seed 20261127 congested 1+1: cycle 733.929 / 158.584 / 640.909 / 302.317. The 20×2 AI regression vs baseline is not stable.
- Live Jira Custom UI journeys and second site still not verified. Feature freeze documented. CG-8 not started.

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
