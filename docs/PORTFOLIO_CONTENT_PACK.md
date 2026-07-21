# Portfolio Content Pack

Reusable copy for a portfolio site or case-study page. All claims here are
cross-checked against [`docs/PUBLIC_CLAIM_REGISTER.md`](PUBLIC_CLAIM_REGISTER.md)
— nothing below asserts more than that register supports.

## Metadata

```text
Title: OpsTwin — Operational Simulation and Decision Lab
Slug: opstwin
Category: Product engineering / decision-support tooling
One-line summary: Paired-simulation evidence for service-operation
  decisions, with an honest boundary between evidence and recommendation.
Role: Product design, architecture, implementation, and verification
Timeline: Sprint 00 (foundation) through Sprint 13 (public release prep)
Status: Core product complete; production deployment live; maintenance
  and portfolio-presentation phase
Stack: Next.js, React, TypeScript, FastAPI, Pydantic, SimPy, Python
Live URL: https://ops-twin.vercel.app
Repository URL: https://github.com/RaulMermans/OpsTwin (private;
  visibility change pending owner approval)
```

## Copy variants

### Card summary (20–30 words)

OpsTwin simulates support-operation changes — like adding staff or
speeding up triage — under matched conditions, then reports the observed
effect with honest uncertainty, not a recommendation.

### Short description (50–70 words)

OpsTwin is a decision-support simulation for service operations. It runs
paired, seeded simulations of a support workflow against candidate
changes, then reports observed cycle-time impact, improvement probability,
and uncertainty — with risk, resource, sensitivity, economic, and
representative-run evidence behind the headline result. It reports
comparative evidence, not a prescriptive answer, and is explicit about
where its evidence stops.

### Overview (120–180 words)

Static dashboards describe what already happened; they don't answer "what
if we changed this?" OpsTwin is a discrete-event simulation (SimPy) behind
a Next.js/FastAPI product that lets someone define a support-operation
baseline and one to three candidate changes, then runs 50 paired
simulations per scenario using a shared random-seed schedule so differences
are attributable to the change, not noise. The result reports observed
cycle-time impact, how often a scenario improved on the baseline, and a
confidence interval — in plain language by default, with risk, resource,
sensitivity, economic, and single-representative-run playback evidence one
click away. A guided, no-edit flow is the default experience; an advanced
workspace preserves full scenario editing. The project also survived a
real production packaging failure and a real usability-redesign cycle,
both documented rather than smoothed over, and is now deployed as a single
Vercel Services project with no database, accounts, or persistence.

### Full case-study narrative (400–700 words)

OpsTwin started from a specific, narrow question: when a support
operation is considering a change — one more Level 1 agent, or a faster
triage step — what actually happens to cycle time, queues, and SLA
attainment? Not "what's our historical average," which any dashboard
already answers, but "what would change, and how confident should we be in
that estimate?"

The answer is a discrete-event simulation built on SimPy rather than a
hand-rolled queueing approximation, wrapped in versioned Pydantic contracts
so that every capability — single runs, repeated runs, scenario
comparison, sensitivity, economics, playback — has an explicit, additive
contract version instead of an implicit shape that could silently change.
The core methodological decision is paired execution: a baseline and every
candidate scenario share the same sequence of random seeds, run for run
(common random numbers), so an observed difference reflects the change
being tested, not sampling noise. Fifty paired runs per scenario expose how
much that difference actually varies, reported as a confidence interval
and an improvement probability — deliberately not framed as a prediction
or a recommendation.

Two usability lessons shaped the product more than any single feature.
First, a deployment incident: production failed at build time because a
frontend module imported a baseline fixture from a directory
(`examples/`) that `.vercelignore` excludes from the deployed bundle. The
fix wasn't just moving the file — it was recognizing that a deployment
ignore-list is an architectural boundary, and adding a regression script
(`verify:vercel-runtime`) that would catch the same mistake again. Second,
a usability audit (automated regression plus expert/heuristic review, not
yet a human participant study) found that a technically complete product
front-loaded mechanics over the decision: baseline and scenario editors
appeared before results, and results themselves sat behind Flow,
Sensitivity, Economics, and Playback rather than leading. The redesign
made a guided, no-edit comparison the default: baseline, two candidate
changes, one run action, an immediate plain-language result, then evidence
one panel at a time. The original full editing workspace didn't go away —
it moved to an explicit Advanced mode.

What shipped is deliberately bounded. There's no database, no
authentication, no persistence, and no arbitrary workflow builder — the
canonical model is a support operation, not a general process-modeling
tool. Sensitivity is strictly one-factor-at-a-time with no interpolation.
Economics only ever uses assumptions a user explicitly supplies — a blank
field stays blank, never a hidden zero. Representative playback shows
exactly one sampled run and says so, distinct from the aggregate metrics
computed across all successful runs.

The product is deployed today as one Vercel Services project — one
repository, one domain, a Next.js web service and a FastAPI simulation
service behind a same-origin API boundary — verified with a real backend
and frontend test suite, both builds, and a production browser walkthrough
across three viewports. What's still open is stated rather than implied: no
five-participant usability study has run yet, no real company's operational
data has been processed, and performance figures are bounded local or
single-deployment measurements, not load-test guarantees. The repository
remains private and unlicensed until its owner makes those decisions
explicitly — deliberately kept separate from "the product works."

### Technical architecture summary

One repository deploys one Vercel Services project containing a Next.js
web service and a FastAPI simulation service behind a same-origin
`/api/simulation/*` boundary. Requests validate against versioned
Pydantic/JSON Schema contracts, execute in a seeded SimPy discrete-event
run, and return audited, integrity-checked evidence. Stateless throughout:
no database, no authentication, no persistence. Exports are generated
client-side from the evidence already returned to the browser.

### Usability iteration summary

An expert/automated audit found a technically complete product that
front-loaded editing mechanics ahead of the decision and buried results
behind four evidence tabs. The redesign made a guided, no-edit comparison
the default — baseline, two changes, one run, an immediate plain-language
result — while preserving full editing in an explicit Advanced mode.
Frontend tests grew from 142 to 172 with no test deleted. No human
participant study has run yet; that's stated, not hidden.

### Verification summary

Backend and frontend test suites, linting, type-checking, both builds,
source packaging, and a production smoke/browser walkthrough are re-run
fresh each release cycle rather than assumed from a prior sprint. Exact
current counts are in `docs/sprints/SPRINT_13_PUBLIC_PORTFOLIO_RELEASE.md`
and cross-referenced in `docs/PUBLIC_CLAIM_REGISTER.md`.

### Limitations summary

Support-operations only, not a general workflow builder. No database,
accounts, or persistence. No real-company data processed. No causal claim,
no optimization guarantee, no autonomous recommendation. Performance
evidence is bounded and local/single-deployment, not a load-test
guarantee. Representative playback is one sampled run, not aggregate
truth. Human usability validation is still pending.

### Lessons summary

Analytical correctness doesn't guarantee usability. Missing assumptions
must stay missing, not silently default to zero. Paired evidence is a
stronger claim than comparing unrelated runs. Deployment packaging is
architecture, not an afterthought. Claims need to be labeled by the kind of
evidence behind them — source, command, or production — not just asserted.

## Portfolio case-study structure

```text
Hero — tagline, live demo link, hero screenshot
Context — support operations, decision-support framing
Problem — dashboards describe the past; the canonical question
Constraints — no database/accounts, canonical model only, bounded scope
Approach — paired simulation, versioned contracts, guided default
Architecture — one repo, one Vercel project, same-origin API, diagram
Key decisions — SimPy, common random numbers, explicit economics
Usability iteration — before/after, evidence, stated limitation
Deployment recovery — the examples/ + .vercelignore incident and fix
Outcome and evidence — test counts, production verification
Limitations — the full honest list, unedited
Reflection — what I learned, in my own words
Live demo CTA — link to https://ops-twin.vercel.app
```

## Metrics (technical/project only — not business outcomes)

```text
247 backend tests
172 frontend tests
7 public API routes
7 versioned contract layers (0.2.0 through 0.7.0)
1 repository
1 Vercel project
2 deployed services (web, simulation)
1 public domain
```

These describe engineering scope and verification depth. They are not
business outcomes, cost savings, or user-impact metrics — none of those
have been measured, because no real-company deployment has occurred.

## Screenshot manifest

| Filename | Section | Caption | Alt text | Key takeaway |
| --- | --- | --- | --- | --- |
| `01-landing.png` | Hero | The landing page framing the canonical decision question | "OpsTwin landing page: 'Test an operating change before the queue feels it,' with links to try the guided comparison or open the advanced workspace." | Decision-first framing, not a dashboard |
| `02-guided-setup.png` | Approach | Guided baseline and two-scenario setup | "Guided setup screen showing the immutable baseline and two candidate scenarios, Add one Level 1 agent and Faster triage, ready to compare." | One immutable baseline, bounded scenario editing |
| `03-guided-result.png` | Outcome and evidence | Plain-language paired-comparison result | "Guided result summary after a 50-run paired comparison, showing observed cycle-time change, improvement probability, and uncertainty range for both scenarios." | Result leads with plain language, not statistics jargon |
| `05-risk-evidence.png` | Key decisions | Risk classification for the comparison | "Risk evidence tab for the completed comparison." | Risk is surfaced, not hidden inside a table |
| `06-resource-evidence.png` | Key decisions | Resource-pool pressure evidence | "Resource evidence tab showing operational pressure on staffing pools." | Structural evidence behind the headline number |
| `07-sensitivity.png` | Key decisions | One-factor-at-a-time sensitivity sweep | "Sensitivity tab after running a one-factor-at-a-time sweep on Level 1 agent capacity, showing the observed response curve and integrity check count." | No interpolation, no hidden curve-fitting |
| `08-economics.png` | Key decisions | Blank economic assumptions shown as unconfigured | "Economics tab with cost assumption fields left blank, illustrating that blank fields remain unconfigured rather than defaulting to zero." | Blank never silently becomes zero |
| `09-playback.png` | Key decisions | Representative run playback | "Representative playback tab showing the baseline representative run's timeline controls and run-level event summary." | One sampled run, explicitly labeled as such |
| `10-advanced-workspace.png` | Architecture / Reflection | Advanced mode's full editing workspace | "Advanced workspace at /workspace?mode=advanced, showing the full editable baseline and scenario controls." | Guided didn't replace Advanced, it added to it |
| `social-preview.png` | (GitHub social card) | Card pairing the tagline with a result screenshot | "OpsTwin: Test an operating change before the queue feels it — paired simulation evidence for service-operation decisions, comparative not prescriptive, with a screenshot of a completed guided comparison result." | Repository link preview |

## SEO copy

```text
SEO title: OpsTwin — Operational Simulation and Decision Lab
Meta description: Paired-simulation evidence for service-operation
  decisions — compare workflow changes under matched conditions, with
  honest uncertainty, sensitivity, economics, and representative playback.
Open Graph title: OpsTwin: Test an operating change before the queue
  feels it
Open Graph description: A simulation-based decision lab for service
  operations, comparing candidate changes with paired stochastic evidence
  instead of guesswork or a single pilot.
Portfolio card tags: simulation, decision-support, discrete-event,
  operations-research, fastapi, nextjs, typescript, python, sensitivity-
  analysis, stochastic-modeling
```

## Builder narrative (for portfolio "how it was built" framing)

The build arc, in order: a deterministic single-run simulation kernel and
its analytical validation; repeated stochastic execution with online
aggregation; paired scenario comparison with common random numbers;
read-only workflow visualization; one-factor-at-a-time sensitivity;
explicit-assumption economics; deterministic representative-run playback;
a first production deployment that failed on a packaging boundary and was
fixed with a regression script, not just a patch; a usability audit that
found the technically complete product hard to use cold, followed by a
guided-mode redesign; and finally this public-release preparation pass.
The arc is deliberately not presented as flawless — the deployment failure
and the usability gap are both first-class parts of the story, with the
fixes and their regression evidence shown alongside them.
