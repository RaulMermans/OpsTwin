# Vercel Preview Evidence

## Status

Preview validation is deferred by explicit user instruction. On 2026-07-16, Vercel CLI `56.2.0` running Node.js `24.14.0` reported no stored credentials; the login flow was not completed. No preview or production deployment was created, and no further remote action should be attempted until the user provides deployment instructions.

## Local Services evidence

`vercel dev -L` recognized both configured services (`web` as Next.js and `simulation` as FastAPI) and selected `http://localhost:3001` because port 3000 was occupied. The Windows Python runner then generated `vc_init_dev.py` with an unescaped `C:\Users\...` entry path; Python rejected `\U` as a truncated Unicode escape. This is a local Vercel CLI path-generation blocker, not a FastAPI import or application error.

The documented separate-process fallback was tested at `http://localhost:3000` with a development-only same-origin rewrite to FastAPI on port 8000:

- `/`: 200, 291 ms, 19,315 bytes.
- `/workspace`: 200, 121 ms, 20,108 bytes.
- health: 200, 17 ms, 50 bytes.
- single summary: 200, 2,406 ms, 3,858 bytes.
- repeated two-run summary: 200, 356 ms, 27,678 bytes.
- 10-run, one-scenario comparison: 200, 1,535 ms, 224,312 bytes.
- invalid comparison: structured 422, 325 bytes.
- over-budget comparison: structured 422, 193 bytes.

Local timings are development evidence only and are not hosting capacity claims.

## Browser evidence

The in-app browser completed landing-to-workspace navigation, health readiness, canonical 50-run comparison, factual ranking, inline invalid-input handling, 30,000-unit work guard, mobile layout measurement, and technical-evidence disclosure. Integrity passed 16 checks. At 390 by 844 CSS pixels, final document width was 375 pixels with no horizontal overflow. Browser error/warning logs were empty.

## Preview record

- Deployment type: preview only; not created.
- Preview URL: not created; remote deployment is deliberately deferred.
- Cold/warm health and comparison timing: not measured.
- Preview payload, hash, structured-error, and browser-console replay: not measured.
- Production: not attempted and not authorized.

ADR-014 therefore remains proposed and GM-051 remains deferred.

## 2026-07-18 addendum

Local Vercel configuration was reviewed and prepared (see `docs/VERCEL_DEPLOYMENT.md` — "Deployment preparation status") without attempting `vercel login`, linking, or a new preview. No new evidence was collected in this entry; the prior 2026-07-16 record above remains the last executed evidence.

## 2026-07-20 — Production deployment evidence (Sprint 11)

### Deployment record

- Vercel project: `ops-twin` (organization `raulmermans-projects`, account `raulmermans`), pre-existing — no new project or repository was created.
- Deployment URL: `https://ops-twin.vercel.app` (also aliased at `https://ops-twin-raulmermans-projects.vercel.app` and `https://ops-twin-git-master-raulmermans-projects.vercel.app`).
- Environment: Production.
- Git branch: `master`.
- Git commit: `1c571ec` (`fix(economics): record sensitivity observer failures safely`), preceded in this sprint by `72607de` (the Vercel runtime hotfix) and `2feb636` (a `smoke:preview`/`smoke:vercel-local` argument-parsing fix). Starting broken commit was `fd1c3f4`.
- Build region: `iad1`.
- Web framework: Next.js `16.2.10` (Turbopack), Node.js `24.x` (Vercel-managed runtime).
- Python runtime: `python3.12` (Vercel Python function runtime for the `simulation` service; the function bundle is 11.18 MB, well under the 500 MB uncompressed limit).
- One Vercel project, one domain, both services (`web`, `simulation`) behind the unchanged root `vercel.json` rewrites: confirmed.

### Starting failure and fix

The prior production deployment (commit `fd1c3f4`) failed at `next build` with `Module not found: Can't resolve '../../../../examples/product/support-operations-baseline.json'`, because `.vercelignore` excludes `examples/` and `apps/web/lib/templates/support.ts` imported a runtime JSON asset from outside `apps/web`. Fixed by packaging a runtime copy of that JSON inside `apps/web/lib/templates/` and adding `pnpm verify:vercel-runtime` as a regression check (see `docs/sprints/SPRINT_11_RUNTIME_AND_FLAGSHIP_POLISH.md`). The new deployment's build log shows `next build` completing (`✓ Compiled successfully`, `✓ Generating static pages using 1 worker (4/4)`) followed by the Python function packaging step, with no missing-module error.

### Deployed route and API evidence

All checks below ran against `https://ops-twin.vercel.app` (warm, after the deployment's first request):

| Route | Status | Duration | Response bytes |
| --- | --- | --- | --- |
| `GET /` | 200 | 514 ms | 12,320 |
| `GET /workspace` | 200 | 90 ms | 29,986 |
| `GET /api/simulation/health` | 200 | 187 ms | 50 |
| `POST /api/simulation/simulate` | 200 | 406 ms | 3,858 |
| `POST /api/simulation/simulate/repeated` | 200 | 354 ms | 27,678 |
| `POST /api/simulation/compare/scenarios` (10 runs, 1 scenario) | 200 | 1,732 ms | 225,280 |
| `POST /api/simulation/compare/scenarios` (25 runs, 1 scenario) | 200 | 3,401 ms | 235,954 |
| `POST /api/simulation/compare/scenarios` (50-run canonical fixture) | 200 | 1,390 ms | 224,312 |
| `POST /api/simulation/compare/scenarios` (`{}`, invalid) | 422 | 305 ms | 325 |
| `POST /api/simulation/compare/scenarios` (500 runs × 1,000 items, over budget) | 422 | 298 ms | 193 |
| `POST /api/simulation/analyze/sensitivity` | 200 | 319 ms | 3,719 |
| `POST /api/simulation/analyze/economics` | 200 | 347 ms | 43,774 |
| `POST /api/simulation/analyze/economic-sensitivity` | 200 | 423 ms | 12,633 |

Health responded `{"status":"ok","service":"opstwin-simulation-api"}`. The 10- and 25-run comparisons both reported `integrity.status: "passed"`; the over-budget request was rejected with `WORK_BUDGET_EXCEEDED` (`estimatedWorkUnits: 1,500,000` against the unchanged 100,000-unit limit) rather than the limit being raised. `pnpm smoke:preview -- https://ops-twin.vercel.app` passed all eight of its checks in full.

All timings above are single-request measurements against one live deployment, not a load test or a hosting-capacity claim; only the deployment's actual work-budget guard behavior (rejecting the 500-run/1,000-item request) is asserted as a property, not the exact millisecond figures.

### Browser evidence

The in-app browser completed the full product journey against the deployed app: landing → `/workspace` → baseline assumptions → the two default scenarios → a 50-run paired comparison → every analysis tab (Overview, Metrics, Risk, Resources, Technical evidence) → Flow → Sensitivity (a live run with `observed mixed` monotonicity and 24 integrity checks) → Economics (a live run with factual, non-prescriptive trade-off wording) → Playback (source toggle between independently-selected baseline/scenario representatives, restart/step/seek/speed/important-event navigation, a 542-row captioned event ledger, and the item journey inspector) → JSON and CSV exports for both the comparison and economics panels. Console and network logs were empty of errors throughout; no request failed; no `localhost` or `127.0.0.1` reference was found in the rendered document. At 390×844, 768×1024, and 1440×900, `document.documentElement.scrollWidth` never exceeded the viewport width; the metric table, event ledger, and analysis tab strip contain their own width inside an `overflow-x: auto` wrapper rather than causing page-level horizontal scroll. Zero elements with a positive `tabindex` and zero unlabeled buttons or inputs were found sitewide.

### Known plan limitations (unchanged)

Function request/response bodies remain subject to Vercel's documented 4.5 MB limit; the product's own comparison-response guard remains a conservative 1 MB uncompressed. The backend work-budget limit remains 100,000 units; the UI ceiling remains 30,000 pending further preview evidence. Services remains a current Vercel beta capability. These single-request timings characterize this deployment at the time of measurement only and make no hosting-capacity claim.
