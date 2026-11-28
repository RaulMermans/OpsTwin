# Codegeist claim register

| Claim | Classification | Evidence |
|---|---|---|
| Desktop tree matched GitHub `master` `cf5a7eb57b13c83018757a522cfcad0117b207ea` | Command verified | `diff -rq` empty vs clone 2026-11-26 |
| Repository is public and MIT licensed | Source verified | `gh repo view`, `LICENSE` |
| Forge CLI 15.1.0 installed; not logged in | Command verified | `forge --version`, `forge whoami` |
| Official Forge skills installed project-scope for Cursor and Claude | Command verified | `forge skills status --json` |
| Core does not depend on Forge | Command verified | `pnpm verify:atlassian-isolation` |
| Live Forge install on OPS | Command verified 2026-11-26 | `forge whoami`; `forge install list` → `opstwin-dev.atlassian.net` / development / `b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815` |
| Live Jira API | Resolver implemented; live body is a separate gate | `getProjectSnapshot` uses `api.asUser()` |
| Live Forge Remote | Unauthenticated POST returns 401 `FIT_INVALID` on production URL | `curl` 2026-11-27 |
| Live CG-1 comparison inside Jira | Two FIT-authenticated synthetic runs on OPS queue page 2026-11-27 | add-capacity +1: 45.913→47.386, P=0.200; faster-triage 25%: 45.913→42.874, P=0.600; 5 paired runs; integrity passed |
| Operational snapshot `os.1.0.0` | Contract + golden fixture + Forge tests | `contracts/operational-snapshot.schema.json` |
| Live Jira/JSM metadata on OPS queue page | Command + browser verified 2026-11-27 | `getProjectSnapshot`/`getRequestTypes` asUser: OpsTwin IT Support Lab (OPS); request types visible |
| Live CG-2 import inside Jira | Development **3.2.0**; resolver invoke recovered | Custom UI import still needs a click in the iframe |
| Differentiation vs JSM WFM / VSA / Marketplace Monte Carlo | Source-verified research | `COMPETITIVE_ANALYSIS.md` |
| Existing-engine interventions for capacity, times, arrivals, routes, failure | Source verified | `registry.py` + `SIMULATION_COMPATIBILITY.md` |
| CG-3 offline calibration | Source + pytest | `app/calibration`, ADR-026 |
| CG-3.1 scientific integrity of calibration | Source + pytest + benchmark matrix | P0 binding, worklogs, holdout, identities; live calibration still not claimed |
| CG-3 live operational calibration | Not claimed | Live snapshot transfer not enabled |
| CG-4 intervention adapters over existing comparison | Source + pytest | `app/interventions`, ADR-027 |
| CG-4 live Jira experiment on OPS | Owner-clicked 2026-11-27 | Golden + assumptions → constructed `32206b92…`; capacity +1/+1, 40×5 paired runs; hosted transform 401 without FIT; Forge development 3.4.0 |
| CG-4 live operational calibration of OPS history | Not claimed | Transform/calibrate remotes remain synthetic fixture-ID only |
| CG-5 multi-scenario native lab | Source + pytest + Forge 3.5.0 + Overview screenshot | `cg5.v1`, `cg5-hybrid-support`; live Overview in OPS 2026-11-27; full experiment click inside Custom UI iframe not completed by agent |
| CG-5 live operational calibration of OPS history | Not claimed | Snapshots stay in Forge; remotes remain fixture-ID only |
| CG-6 decision overlay (cash vs capacity, ROI, payback, break-even) | Source + pytest + Forge 3.6.0 | `app/economics/decision.py`, `cg6.v1`; hosted `dpl_GHxMygNfRXUrCosM8Q8AAcjFNhvK`; live Jira economic click not completed |
| CG-6 live organizational ROI | Not claimed | Synthetic demonstration assumptions only |
| CG-7 BYOD + signed evidence | Source + pytest + hosted 3.7.0; live Jira clicks not completed | ADR-030, `construct-baseline`, HMAC on Vercel prod; Forge 3.7.0; iframe journeys pending owner session |
| CG-7.1 CSV `os.1.0.0` pipeline | Source + pytest | Template parses, validates, and constructs an exploratory model; malformed files refused |
| CG-7.1 trusted Jira extraction | Source + Forge tests | Resolver re-extracts; `trustedExtraction` required; browser snapshots rejected |
| CG-7.1 artifact project/principal scope | Source + pytest | Cross-project, cross-principal, and wrong-purpose tokens rejected |
| CG-7.1 financial feasibility | Source + pytest | Implausible busy hours withhold cash; realistic golden ROI 0.5 |
| CG-7.1 live Jira journeys | Not claimed | Custom UI iframe acceptance still requires owner session |
| CG-7.1 second-site isolation | Not claimed | No second installation |
| CG-7 historical organizational calibration | Not claimed | Exploratory models only unless holdout passes |
