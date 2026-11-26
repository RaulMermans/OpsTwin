# Codegeist claim register

| Claim | Classification | Evidence |
|---|---|---|
| Desktop tree matched GitHub `master` `cf5a7eb57b13c83018757a522cfcad0117b207ea` | Command verified | `diff -rq` empty vs clone 2026-11-26 |
| Repository is public and MIT licensed | Source verified | `gh repo view`, `LICENSE` |
| Forge CLI 15.1.0 installed; not logged in | Command verified | `forge --version`, `forge whoami` |
| Official Forge skills installed project-scope for Cursor and Claude | Command verified | `forge skills status --json` |
| Core does not depend on Forge | Command verified | `pnpm verify:atlassian-isolation` |
| Live Forge install on OPS | Blocked | `forge whoami` → Not logged in |
| Live Jira API | Blocked | no authorized token |
| Live Forge Remote | Not implemented as hosted endpoint | no `remotes:` in manifest |
| Differentiation vs JSM WFM / VSA / Marketplace Monte Carlo | Source-verified research | `COMPETITIVE_ANALYSIS.md` |
| Existing-engine interventions for capacity, times, arrivals, routes, failure | Source verified | `registry.py` + `SIMULATION_COMPATIBILITY.md` |
