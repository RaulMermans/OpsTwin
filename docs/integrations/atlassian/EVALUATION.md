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
| Live Forge Remote | code complete; hosted FIT invoke depends on Vercel deploy of the new route |
