# OpsTwin Scratchpad

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
