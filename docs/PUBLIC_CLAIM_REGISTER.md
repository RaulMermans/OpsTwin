# Public Claim Register

This register tracks every claim intended for public-facing material
(`README.md`, `docs/PORTFOLIO_CONTENT_PACK.md`, social-preview copy) against
its evidence. It exists so that public materials only assert what has
actually been verified, not what would merely be convenient to say.

## Classification key

- **Source verified** — true by direct inspection of code or contracts.
- **Command verified** — true because a specific command was executed and
  its output recorded.
- **Production verified** — true because the live deployment at
  `https://ops-twin.vercel.app` was directly exercised (smoke script or
  browser walkthrough) and recorded.
- **Design rationale** — an architectural or product decision, not an
  empirical measurement.
- **Known limitation** — an honest boundary statement, not a positive claim.
- **Owner statement** — a first-person statement about the author's own
  role or process, not independently falsifiable.
- **Unsupported** — no evidence exists; must not appear in public material.

## Register

| Claim | Classification | Evidence |
| --- | --- | --- |
| Production deployment is live at `https://ops-twin.vercel.app` | Production verified | `docs/VERCEL_DEPLOYMENT.md`, `docs/VERCEL_PREVIEW_EVIDENCE.md` (Sprint 11 route/timing table), Sprint 13 fresh `pnpm smoke:preview` run (`docs/sprints/SPRINT_13_PUBLIC_PORTFOLIO_RELEASE.md`) |
| Backend test suite passes | Command verified | Sprint 13 fresh `pnpm test` run: 247 passed. See `docs/sprints/SPRINT_13_PUBLIC_PORTFOLIO_RELEASE.md` |
| Frontend test suite passes | Command verified | Sprint 13 fresh `pnpm test:web` run: 172 passed across 22 test files. See `docs/sprints/SPRINT_13_PUBLIC_PORTFOLIO_RELEASE.md` |
| Lint, typecheck, and both builds pass | Command verified | Sprint 13 fresh `pnpm lint` (ESLint + Ruff), `pnpm typecheck` (tsc + mypy strict, 51 source files), and `pnpm build` (Next.js + FastAPI) all passed |
| Guided mode is the default session presentation | Source and production verified | `apps/web/app/workspace/page.tsx` (`resolveInitialMode`), Sprint 12/12.1 sprint docs, production browser walkthrough |
| Advanced mode is reachable at `/workspace?mode=advanced` | Source and production verified | `resolveInitialMode` validated search-parameter handling; production browser walkthrough |
| Paired simulations use matched seeds (common random numbers) | Source and specification verified | `docs/SCENARIO_COMPARISON_SPEC.md` (0.5.0), ADR-012 |
| Improvement probability and confidence intervals are reported, not certainty | Source and specification verified | `docs/SCENARIO_COMPARISON_SPEC.md`: "Results are simulation evidence and comparative ranking, not causal proof, optimization, or operational recommendations." |
| Sensitivity is one-factor-at-a-time with no interpolation | Source and specification verified | `docs/SENSITIVITY_ANALYSIS_SPEC.md`: "No interpolation or extrapolation is performed"; "does not establish causality, find an optimum, or measure interactions" |
| Economics uses only explicit user-supplied cost assumptions; blank is not zero | Source and specification verified | `docs/ECONOMIC_COMPARISON_SPEC.md` (0.7.0); economics evaluator distinguishes unavailable/not-configured from zero |
| Representative playback shows one sampled run, not aggregate truth | Source and specification verified | `docs/REPRESENTATIVE_PLAYBACK_SPEC.md`: "without presenting that one run as aggregate certainty" |
| Deployment incident: `examples/` import broke `.vercelignore`-stripped Turbopack build, fixed by a runtime-owned copy plus a regression script | Source and production verified | `docs/sprints/SPRINT_11_RUNTIME_AND_FLAGSHIP_POLISH.md`, `docs/VERCEL_PREVIEW_EVIDENCE.md`, `scripts/verify-vercel-runtime.mjs` |
| Frontend test count grew from 142 to 172 across Sprint 12.1 without deleting tests | Source verified | `docs/sprints/SPRINT_12_1_GUIDED_USABILITY_CLOSURE.md`, `SCRATCHPAD.md` |
| Five-participant human usability study completed | Unsupported | Must not be claimed. `docs/USABILITY_TEST_PLAN.md` describes it as planned, not executed; `docs/USABILITY_FINDINGS.md` states all evidence to date is automated regression, expert/heuristic review, owner walkthrough, and production browser QA |
| Usability iteration is evidenced by automated regression, expert review, owner walkthrough, and browser QA | Known limitation / Command + Production verified | `docs/USABILITY_FINDINGS.md`; explicitly not a substitute for participant testing |
| No database, authentication, or persistence exists | Source verified | `docs/ARCHITECTURE.md`: "There is no database, worker, graph engine, or external service." |
| Performance figures are bounded local/single-deployment measurements, not load-test guarantees | Known limitation | `docs/PERFORMANCE_BASELINE.md`, `docs/VERCEL_PREVIEW_EVIDENCE.md`: "single-request measurements against one live deployment, not a load test or a hosting-capacity claim" |
| The canonical model covers support operations, not arbitrary workflows | Known limitation | `docs/SCENARIO_LAB_SPEC.md` deferred-scope list; `docs/PROJECT_BRIEF.md` |
| No real-company operational outcome has been measured | Known limitation | No such evidence exists anywhere in the repository; absence confirmed by audit |
| Development was AI-assisted with human-directed scope, architecture, and acceptance criteria | Owner statement | Author statement; cross-checked against this repository's own sprint/ADR discipline (every behavior change requires an executable verification path, per `CLAUDE.md`) |
| The project is open source | Unsupported | No `LICENSE` file exists in the repository (confirmed by audit); must not be claimed until an owner selects and adds a license |
| The repository is public | Unsupported | Repository visibility remains private as of this sprint; owner decision pending |

## Process note

This register is updated whenever a new public-facing claim is added to
`README.md` or `docs/PORTFOLIO_CONTENT_PACK.md`. A claim with no row in this
table should not appear in public material.
