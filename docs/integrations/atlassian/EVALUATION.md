# Evaluation notes

Standalone product claims remain in `docs/PUBLIC_CLAIM_REGISTER.md`.

Atlassian-layer claims allowed only with evidence:

| Claim | Status |
|---|---|
| Forge foundation builds Custom UI | command-verified after `npm run build` |
| FIT rejection cases | unit-tested |
| Empty vs permission API outcomes | unit-tested |
| Live queue page on OPS | development install listed 2026-11-26; page content re-checked in CG-1 |
| Live Jira API | implemented in resolver; live response is an acceptance gate |
| Live Forge Remote | unauthenticated hosted POST returned 401 FIT_INVALID on 2026-11-27 |
| Operational snapshot contract | golden fixture validates in Python and Node |
| Live CG-2 import UI | development **3.1.0** deployed 2026-11-27; install `b1bb872d-...` latest on major 3 |
| Offline CG-3 / CG-3.1 calibration engine | pytest `test_calibration_*`; full benchmark matrix seeds 1–3; synthetic fixture remote only |
| Live operational calibration | not claimed |
