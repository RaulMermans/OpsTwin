# Risk register — OpsTwin for Jira

| ID | Risk | Severity | Likelihood | Impact | Owner | Mitigation | Trigger | Contingency | Status |
|---|---|---|---|---|---|---|---|---|---|
| R1 | Forge login not completed before CG-1 | High | High | No live install | Owner | Document exact `forge login` steps | `forge whoami` fails | Continue local foundation | **Closed 2026-11-26 — `forge whoami` succeeded** |
| R2 | Developer Space / app registration delayed | High | Medium | Cannot deploy | Owner | Distinct OpsTwin space, no RE:VERSE reuse | `forge register` blocked | Keep unregistered scaffold | **Closed — OpsTwin space and app id present** |
| R3 | Runs on Atlassian ineligibility from Remote | Medium | Certain given architecture | Bonus prize only | Product | Do not claim that bonus | Eligibility FAQ | Compete on main category | Accepted |
| R4 | Pre-existing OSS disclosure insufficient | High | Medium | Submission validity | Owner | Disclose OpsTwin engine as pre-existing MIT; Forge layer is new | Organizer question unanswered | Send prepared question | Open |
| R5 | 25s Remote timeout vs comparison work | High | Medium | Live demo failure | Eng | summary mode, small runCount, work-budget check | First Remote latency test | Precompute demo fixture **labeled as such** — never fake live | Open |
| R6 | JSM project empty / no history | Medium | High | Weak calibration story | Eng | Schema-first demo + synthetic OPS issues only with owner approval | Search returns empty | Use canonical support baseline with explicit “not this tenant’s history” | Open |
| R7 | Status-time mistaken for handling time | High | High | Wrong model | Eng | Document bias; prefer worklogs when present | Calibration sprint | Leave processing as assumption | Open |
| R8 | Shared seeds + routing changes | Medium | Medium | Invalid pairing | Eng | Disclose stream break; keep topology stable in demo | Route overrides used | Prefer capacity/time overrides for flagship demo | Open |
| R9 | Production API accidentally Forge-auth coupled | High | Low | Breaks standalone app | Eng | ADR-023/024, isolation script, dedicated integration prefix | PR mutates `/api/simulation/*` auth | Revert | Mitigated: new prefix only |
| R15 | Hosted remote route absent on Vercel | High | High | No live FIT invoke | Owner | Deploy CG-1 branch to `ops-twin` | Unauthenticated 404/401 on the integration path | Mark `remote_live_invocation_status` blocked | **Closed 2026-11-27 — unauthenticated POST returns 401 FIT_INVALID** |
| R16 | CG-1 live asUser bodies not captured in this session | Medium | Medium | Entry-gate partial | Eng | Resolver + install list | Queue page not exercised | Continue CG-2 offline | Open |
| R17 | Interactive import timeout | High | Medium | Partial snapshots | Eng | 20s deadline, stage budgets, Retry-After vs remaining time | Resolver timeout | Return partial; async only after measurement | Mitigated in CG-2.1 |
| R18 | User context lost if async continuation added later | High | High | Silent asApp escalation | Eng | No async import in CG-2 | Proposal to queue imports | Keep synchronous asUser | Mitigated |
| R19 | Empty OPS history | Medium | High | Empty live snapshot | Eng | Explicit empty state + synthetic demo | Search returns [] | Owner-approved sandbox batch | Open |
| R20 | Status residence treated as service time | High | High | False bottleneck claims | Eng | Separate interval types + UI limitations | CG-3 mapping | Keep unresolved operationalClass | Mitigated in CG-2 |
| R21 | Synthetic live tickets misread as history | High | Medium | False evidence | Eng | syntheticOrigin + labels | Fixture writes | Dry-run tool only | Mitigated |
| R22 | Cross-tenant snapshot leakage | High | Low | Privacy incident | Eng | No shared storage; session only | Persistence added | Recheck auth before KVS get | Mitigated |
| R23 | Snapshot size / Forge quotas | Medium | Medium | Failed imports | Eng | Record limit 40 | Latency budget exceeded | Lower limit | Open |
| R24 | Core polluted with Jira types | High | Low | ADR-023 breach | Eng | isolation script + os.1.0.0 in contracts | PR imports @forge in Core | Revert | Mitigated |
| R10 | Credential leak in git or logs | High | Low | Security incident | Eng | gitignore, FIT sanitizer, public-release scan | Secret pattern in CI | Rotate tokens | Mitigated locally |
| R11 | Forge CLI 15 vs 16 mismatch | Low | Medium | Deploy friction | Eng | Upgrade only if 15 fails on register/deploy | CLI error citing 16 | `npm install -g @forge/cli@latest` with owner OK | Watch |
| R12 | MCP not loaded in agent session | Low | High | Weaker Forge docs lookup | Eng | New session after `.cursor/mcp.json` | MCP tools absent | Official docs already retrieved | Open |
| R13 | Judges treat product as dashboard wrapper | High | Medium | Scoring on implementation | Product | Live paired run in Jira, not screenshots of Vercel | Demo script | CG-5 native UX | Open |
| R14 | Billing/subscription change on opstwin-dev | Medium | Low | Policy breach | Owner | No plan changes without approval | Admin console prompts | Stop | Constraint |
| R25 | Unidentifiable service times treated as dwell | High | High | Invalid model | Eng | Refuse status-residence estimates | CG-3 mapping | Assumption or refuse | Mitigated in CG-3 tests |
| R26 | Capacity inferred from assignees | High | Medium | False staffing | Eng | Assumption-only capacity | Assignee counts used as FTE | Refuse | Mitigated |
| R27 | Holdout leakage | High | Medium | Fake validation | Eng | Training-only estimation tests | Thresholds changed after eval | Fail the sprint | Mitigated |
| R28 | Synthetic circularity | Medium | High | Overclaim | Eng | Misspecified/nonstationary profiles | Recovery treated as reality | Claim register | Mitigated |
| R29 | Unsafe snapshot egress | High | Medium | Privacy | Eng | Minimized snapshots only, FIT, HMAC, no issue text | Unbounded payload | Keep size limits | Open in CG-7 |
| R35 | Browser-forged Jira snapshots | High | High | Fake provenance | Eng | Resolver re-extract + trustedExtraction | Browser snapshot posted as jira | Reject | Mitigated in CG-7.1 |
| R36 | CSV schema invalid vs advertised upload | High | High | Broken input mode | Eng | Canonical os.1.0.0 adapter | Template fails validator | Disable CSV | Mitigated in CG-7.1 |
| R37 | Impossible busy hours converted to cash | High | High | False investment case | Eng | Staffed-hour feasibility check | ROI with 12000 h from 20 cases | Withhold cash | Mitigated in CG-7.1 |
| R33 | Browser-forged economic metrics | High | High | False ROI | Eng | Signed evidence tokens | Economics without token | Reject | Mitigated in CG-7 |
| R34 | Finite workload annualized as cash | High | High | False payback | Eng | Explicit evaluation basis | Recurring without demand | Withhold ROI | Mitigated in CG-7 |
| R30 | Deadline-driven scope into CG-4 | Medium | High | Unvalidated interventions | Eng | Stop after CG-3.1 scientific closure | Intervention code in this branch | Revert | Closed into CG-5 |
| R32 | Multi-scenario timeout on Forge 25s | High | Medium | Incomplete live comparison | Eng | Default 20 items × 5 runs, shared baseline | Live duration exceeds budget | Drop to 20×2 and label exploratory | Open |
| R31 | Silent template defaults for estimated routing/service | High | High | Model disagrees with estimates | Eng | Bind or refuse; structural vs empirical origin | Hardcoded route p=1 | Parameter-binding tests | Mitigated in CG-3.1 |
