# Validation Plan

## Method

Golden models use explicit values, nearest-rank p95, and `pytest.approx(abs=1e-9)` for floating-point ratios. Fixed fixtures assert exact event/lifecycle arithmetic; seeded fixtures assert exact standard-library samples and stable serialized results.

## Sprint 12 usability presentation regressions

Web tests assert Guided default state, the valid no-edit default request, result-first rendering, response-owned metric direction and paired uncertainty/probability text, non-prescriptive result language, evidence navigation, advanced control availability, orientation dismissal, glossary access, and unchanged comparison request/export boundaries. Participant usability targets and worksheets are documented in `USABILITY_TEST_PLAN.md`; automated checks are not human-study evidence.

## GM-001 — No queue

**Purpose:** Validate uncongested FIFO flow. **Input:** fixed arrivals slower than fixed service. **Expected/exact:** every wait and maximum queue are zero; utilization is below one. **Failure indicates:** incorrect resource acquisition or horizon math.

## GM-002 — Growing queue

**Purpose:** Preserve Sprint 00 arithmetic. **Input:** five arrivals `[0,5,10,15,20]`, one resource, duration `8`. **Expected/exact:** starts `[0,8,16,24,32]`, waits `[0,3,6,9,12]`, cycles `[8,11,14,17,20]`, averages `6/8/14`, p95 `20`, queue `2`, utilization `1`, SLA `1`. **Failure indicates:** deterministic scheduling or metric regression.

## GM-003 — Equal arrival and processing interval

**Purpose:** Validate ties. **Input:** three items with arrival and processing intervals of `5`. **Expected/exact:** waits `[0,0,0]`; arrival is observed before equal-time release, so maximum queue is transiently `1`; sequence is repeatable and no delay accumulates. **Failure indicates:** unstable same-time ordering.

## GM-004 — Seed reproducibility

**Purpose:** Validate run isolation. **Input:** stochastic arrivals/processing/routing/failure with an explicit seed. **Expected/exact:** same seed has identical arrivals, samples, routes, failures, events, and metrics; a different seed changes at least one sample. **Failure indicates:** global or unordered state.

## GM-005 — Probability routing

**Purpose:** Validate one seeded route decision. **Input:** two options summing to one. **Expected/exact:** every item selects one valid option and fixed-seed counts repeat; invalid sums reject. **Failure indicates:** cumulative selection or validation error.

## GM-006 — Failure and rework

**Purpose:** Validate bounded loops. **Input:** probability-one failure and a finite rework allowance. **Expected/exact:** failure/rework counts equal the configured allowance, completion count remains zero after terminal failure, and no duplicate completion exists. **Failure indicates:** off-by-one or unsafe loop handling.

## GM-007 — Shared resource pool

**Purpose:** Validate cross-stage contention. **Input:** two stages reference one capacity-one pool. **Expected/exact:** maximum concurrent usage is one, waits include contention, and utilization is calculated once. **Failure indicates:** duplicated resources or pool accounting.

## GM-008 — Priority queue

**Purpose:** Validate non-preemptive stable priority. **Input:** active low-priority work followed by queued low and high priority items. **Expected/exact:** active work finishes, high priority starts next, and equal priority retains FIFO. **Failure indicates:** preemption or unstable queue ordering.

## GM-009 — Multi-stage lifecycle

**Purpose:** Validate route and visit reconciliation. **Input:** deterministic two-stage flow. **Expected/exact:** valid route events, exact visit/start/completion times, one final completion, original-to-final cycle, and reconciled stage/pool totals. **Failure indicates:** lost lifecycle state or double counting.

## GM-010 — Exact time-weighted areas

**Purpose:** Prove deterministic state integration. **Input:** five simultaneous items, capacity one, service time ten, measured over forty minutes. **Expected/exact:** queue area `30`, time-weighted queue `0.75`, WIP area `70`, time-weighted WIP `1.75`, busy-capacity time `40`, utilization `1`, arrival/completion rates `0.125`, and flow efficiency `40/70`. **Failure indicates:** snapshot averaging, wrong interval clipping, or an immediate grant counted as waiting.

## GM-011 — Warm-up boundary and incomplete population

**Purpose:** Prove real state carries across warm-up while lifecycle averages remain explicit. **Input:** work active before a `[9, 19)` window. **Expected/exact:** two window arrivals, one completion during the window, two pre-warm-up items, two incomplete window arrivals, two items active at end, time-weighted WIP `2`, time-weighted queue `1`, and no excluded lifecycle duration in included averages. **Failure indicates:** resetting state at warm-up or silently mixing populations.

## GM-012 — M/M/1 theory

**Purpose:** Validate long-run stochastic queue behavior. **Input:** one Poisson source with `lambda = 0.5`, one exponential server with `mu = 1`, warm-up `2,000`, duration `10,000`, fixed seed, and 8,000 generated items. **Expected/tolerance:** measured `rho`, `W`, `Wq`, `L`, and `Lq` are within 15% relative error of queueing theory. **Recorded result:** `rho=0.519578`, `W=2.050743`, `Wq=1.051938`, `L=1.066797`, `Lq=0.547218`; all relative errors are below 9.5%. **Failure indicates:** incorrect stochastic sampling, warm-up handling, or state integration.

## GM-013 — Little's Law

**Purpose:** Reconcile independent rate, duration, and state metrics. **Input:** the GM-012 stable measurement window. **Expected/tolerance:** measured `L` equals measured completion rate times `W`, and `Lq` equals measured completion rate times `Wq`, within 5% relative error. **Recorded result:** completion rate `0.5202`; `L` relative error `2.1e-16` and `Lq` relative error `0`. **Failure indicates:** inconsistent populations or time bases.

## GM-014 — Integrity invariants

**Purpose:** Prevent invalid evidence from reaching metrics or callers. **Input:** valid evidence plus direct malformed variants. **Expected/exact:** valid runs report all 16 checks passed; duplicate completion, missing release, capacity violation, timestamp regression, and lifecycle mismatch each raise a structured integrity error. **Failure indicates:** missing lifecycle, ordering, route, or resource safeguards.

## GM-015 — Route convergence

**Purpose:** Validate repeated probability selection without relying on a brittle exact sequence. **Input:** 5,000 fixed arrivals and a two-option route with probability `0.3`, fixed seed. **Expected/tolerance:** observed proportion is within absolute `0.03`, all selections are valid, and the same seed reproduces the result. **Failure indicates:** biased cumulative routing or nondeterministic state.

## GM-016 — Failure convergence

**Purpose:** Validate repeated Bernoulli failure sampling. **Input:** 5,000 independent stage visits with failure probability `0.25`, fixed seed. **Expected/tolerance:** observed terminal-failure proportion is within absolute `0.03`, and the same seed reproduces the result. **Failure indicates:** biased failure sampling or incorrect terminal accounting.

## GM-017 — Result-detail invariance

**Purpose:** Bound returned evidence without altering simulation truth. **Input:** one seeded run in summary, sampled, and full modes. **Expected/exact:** core metrics, observation metadata, integrity status, seed, and total event count are identical; summary includes zero events; sampled includes complete histories for the deterministic selected subset; full includes every canonical event. **Failure indicates:** filtering before metrics or random sampling side effects.

## GM-018 — Performance and payload baseline

**Purpose:** Record reproducible scaling evidence without deployment claims. **Input:** fixed-seed deterministic runs at 100, 1,000, and 10,000 items. **Expected:** all integrity checks pass, event count scales at eight per item, summary payload remains bounded, and full payload growth is measured. Exact measurements and environment are recorded in `PERFORMANCE_BASELINE.md`. **Failure indicates:** benchmark drift, evidence loss, or an unbounded summary contract.

## GM-019 — Repeated-request reproducibility

**Purpose:** Prove the complete repeated result is replayable. **Input:** the same model, base seed, run count, observation, thresholds, and representative settings twice. **Expected/exact:** serialized `0.4.0` results are byte-equivalent, including child seeds, aggregates, risks, failures, diagnostics, representative index/seed/evidence, and integrity. **Failure indicates:** hidden global state, unstable iteration, or nondeterministic serialization.

## GM-020 — Child-seed schedule

**Purpose:** Freeze index-stable deterministic seed derivation. **Input:** base seed `42`. **Expected/exact:** indices zero through four yield `6085284259181818738`, `278651779053087998`, `14840890843343779510`, `11043869433078333928`, and `8217744721944257512`; prefixes of 50 and 100 agree and the first 500 are unique. **Failure indicates:** byte-order, encoding, hash, index, or random-state drift.

## GM-021 — Online moments

**Purpose:** Validate numerically stable scalar aggregation. **Input:** values `[1, 2, 3, 4]`. **Expected/exact:** count `4`, mean `2.5`, sample variance `5/3`, standard deviation `sqrt(5/3)`, minimum `1`, and maximum `4`. **Failure indicates:** population variance, recurrence, or finalization error.

## GM-022 — Nearest-rank quantiles

**Purpose:** Fix percentile semantics. **Input:** values one through ten. **Expected/exact:** p10 `1`, p50 `5`, and p90 `9`. **Failure indicates:** interpolation or zero-based-rank drift.

## GM-023 — Mean confidence interval

**Purpose:** Validate the disclosed normal approximation and reliability flag. **Input:** `[1, 2, 3, 4]` at 95% confidence. **Expected/exact:** bounds `1.2348486781389878` and `3.765151321861012`, with reliability false; a 30-value sample is marked reliable. **Failure indicates:** wrong standard error, z value, or disclosure threshold.

## GM-024 — Threshold risk

**Purpose:** Validate violation probability and denominator. **Input:** controlled successful snapshots, explicit SLA/cycle/p95/queue/failure thresholds, plus omitted thresholds. **Expected/exact:** each probability equals violating successful runs divided by successful runs, directionality is metric-specific, failed runs are excluded, and omitted thresholds yield no result. **Failure indicates:** reversed comparison, mixed population, or implicit thresholding.

## GM-025 — Representative selection

**Purpose:** Make representative evidence deterministic and central. **Input:** controlled five-dimensional snapshot vectors. **Expected/exact:** min-max normalization, component medians, Euclidean distance, zero contribution for zero-range dimensions, and lowest run-index tie-breaking select the documented candidate. **Failure indicates:** scale bias, mean substitution, or unstable ties.

## GM-026 — Failed-run policy

**Purpose:** Prevent partial repeated results from masquerading as complete evidence. **Input:** injected validation, integrity, execution, and serialization failures plus controlled success ratios. **Expected/exact:** failures have safe categories and run identity, are excluded from aggregates, successful/failed counts reconcile, and ratios below `minimumSuccessfulRunRatio` raise a safe repeated-simulation error. **Failure indicates:** swallowed failures, unsafe exception leakage, or contaminated aggregates.

## GM-027 — Bounded repeated retention

**Purpose:** Ensure repetition does not multiply full histories. **Input:** instrumented repeated runs with a detailed representative. **Expected/exact:** every ordinary run requests summary, only scalar snapshots survive iteration, at most one single-run result is retained at once, and exactly one representative seed is rerun with configured detail. **Failure indicates:** unbounded event/result retention or accidental detailed ordinary runs.

## GM-028 — Convergence diagnostics

**Purpose:** Provide bounded inspectable stabilization evidence. **Input:** repeated runs spanning configured checkpoints. **Expected/exact:** checkpoints are ordered, unique, no greater than requested run count, include the final count, and report cumulative means plus absolute and relative changes from the preceding checkpoint. **Failure indicates:** future-run leakage, unbounded diagnostics, or incorrect deltas.

## GM-029 — Repeated performance and payload baseline

**Purpose:** Record sequential repeated-run cost and retention behavior without hosting claims. **Input:** fixed-seed matrices at 100 items × 10/100 runs and 1,000 items × 10/50 runs. **Expected:** zero failures, aggregate integrity passes, returned event evidence belongs only to one representative rerun, maximum retained single-run results is one, and measurements are recorded in `REPEATED_RUN_PERFORMANCE.md`. **Failure indicates:** scaling drift, hidden retention, or broken repeated accounting.

## GM-030 — Allowed override application

**Expected/exact:** one approved capacity replacement changes only that field, preserves the baseline, validates the scenario, and records exact before/after metadata. **Automated by:** `test_scenario_materializer.py`.

## GM-031 — Invalid override rejection

**Expected/exact:** unknown entity types/IDs, unsupported fields or operations, wrong value types, and duplicate targets reject safely. **Automated by:** comparison model and materializer tests.

## GM-032 — Baseline immutability

**Expected/exact:** independent deep copies preserve the baseline canonical JSON, do not cross-mutate, and produce deterministic SHA-256 model hashes. **Automated by:** materializer and comparison reproducibility tests.

## GM-033 — Paired seed schedule

**Expected/exact:** baseline then each scenario receives the same deterministic seed at every run index; ordinary detail is summary with zero retained events. **Automated by:** instrumented coordinator test.

## GM-034 — Paired delta calculation

**Input:** paired baseline `[10, 20, 30, 40]` and scenario `[8, 18, 33, 44]`. **Expected/exact:** deltas `[-2, -2, 3, 4]`, mean `0.75`, sample variance `10.25`, nearest-rank p10/p50/p90 `-2/-2/4`, and 95% mean interval `[-2.387473248223959, 3.887473248223959]`; absolute tolerance `1e-9`. **Automated by:** comparison metric tests.

## GM-035 — Improvement probability

**Expected/exact:** higher- and lower-is-better fixtures reconcile improved, degraded, and tied counts and probabilities over paired runs; tolerance `1e-9`. **Automated by:** comparison metric tests.

## GM-036 — Relative delta zero behavior

**Expected/exact:** nonzero baselines produce `(scenario-baseline)/baseline`; zero baselines produce `null`, increment the undefined count, and never produce infinity or an exception. **Automated by:** comparison metric tests.

## GM-037 — Comparison reproducibility

**Expected/exact:** identical request runs produce equal hashes, seeds, aggregates, deltas, rankings, and representative evidence; baseline input remains byte-equivalent. **Automated by:** coordinator reproducibility test.

## GM-038 — Comparative ranking

**Expected/exact:** invalid or guardrail-failing scenarios are excluded. Remaining scenarios sort by directed objective delta, improvement probability, narrower confidence interval, then lexicographic scenario ID; explanations disclose the ordering. **Automated by:** ranking tests.

## GM-039 — Scenario failure isolation

**Expected/exact:** one invalid/failing scenario is visible and unranked while baseline and unrelated valid scenarios remain valid. Baseline failure invalidates the request. **Automated by:** coordinator failure-policy tests.

## GM-040 — Comparison integrity

**Expected/exact:** valid evidence passes all comparison checks; controlled hash, seed, paired-index, delta, ranking, representative, retention, work, and override corruptions raise `ComparisonIntegrityError`. **Automated by:** comparison integrity tests.

## GM-041 — Scenario comparison performance

**Expected:** the four required sequential matrices use summary ordinary runs, retain at most two event-rich representatives, pass integrity, and report work, duration, events, payload, success, failure, and paired-ratio evidence. **Recorded in:** `SCENARIO_COMPARISON_PERFORMANCE.md`.

## Deployable decision slice gates

### GM-042 — Canonical product fixture

**Status:** passed. The product baseline and comparison fixtures validate, preserve stable identities, use sampled representatives, stay within 30,000 UI work units, replay byte-identically, and remain below the 1 MB response guard.

### GM-043 — Baseline form mapping

**Status:** passed. Tests prove the eight defaults map to immutable canonical model copies.

### GM-044 — Guided scenario mapping

**Status:** passed. Demand, staffing, process, and quality changes emit supported final replacement values; duplicate targets and more than three scenarios are rejected.

### GM-045 — Client safety boundary

**Status:** passed. The client uses relative `/api/simulation` paths, runtime-checks unknown JSON, requests sampled evidence only, and stops work above 30,000 units.

### GM-046 — Public API errors

**Status:** passed. Request, nested model, work-budget, execution, integrity, comparison, and unexpected failures return stable public envelopes without raw exceptions.

### GM-047 — Product journey

**Status:** passed locally. Browser QA completed health, comparison, rerun-ready results, inline validation, work guard, ranking table, and technical disclosure.

### GM-048 — Accessibility and responsive behavior

**Status:** passed locally. Semantic labels/regions/tables, live loading text, keyboard-native controls, visible status text, reduced motion, and a 390×844 no-overflow measurement were verified.

### GM-049 — Same-origin local routing

**Status:** passed by documented fallback. All public web/API smoke routes passed through localhost:3000. Native `vercel dev -L` service startup is blocked by Vercel CLI 56.2.0 Windows path escaping and is recorded separately.

### GM-050 — Payload boundary

**Status:** passed. Canonical sampled comparison responses are under 1,000,000 uncompressed JSON bytes and ordinary runs retain zero events.

### GM-051 — Preview deployment

**Status:** deferred by explicit user instruction. No preview was created and no further remote action is authorized. ADR-014 remains proposed.

### GM-052 - Production safety and audit

**Status:** passed. No production deployment, commit, push, persistence, secret, alternate API host, or recommendation claim was introduced.

## Carried-forward local product completion gates

### GM-053 - Scenario result statuses

**Status:** partial. **Expected:** ranked, eligible-unranked, guardrail-ineligible, invalid, execution-failed, insufficient-valid, insufficient-paired, completed-unranked, and unknown results map to visible safe text. **Actual:** the centralized adapter and focused cases are implemented and typechecked; the Vitest cases could not execute because Vite child-process startup is sandbox-blocked.

### GM-054 - Optional guardrail control

**Status:** partial. **Expected:** disabled omission, metric-owned direction/unit, valid threshold mapping, backend-owned pass/fail, and accurate no-guardrail copy. **Actual:** source mapping and focused tests cover SLA, cycle, p95, queue, and resource utilization; TypeScript and ESLint pass, but the behavioral suite is blocked.

### GM-055 - Risk comparison presentation

**Status:** partial. **Expected:** baseline/scenario violation probabilities, percentage-point difference, factual direction, and four transition counts render from returned evidence. **Actual:** the Risk view is implemented with textual equivalents; browser and Vitest execution are blocked.

### GM-056 - Request lifecycle

**Status:** partial. **Expected:** duplicate submission prevention, distinct abort/timeout copy, retry, input preservation, network/unexpected errors, and stale-response protection. **Actual:** the client and workspace implement these states and direct TypeScript/ESLint pass; request tests are authored but blocked at Vitest startup.

### GM-057 - Result accessibility

**Status:** partial. **Expected:** labelled controls, associated errors, live feedback, keyboard analysis navigation, accessible tables, status text, and text equivalents. **Actual:** semantic source and focused assertions are present; runtime assistive-technology and browser keyboard checks are blocked.

### GM-058 - Frontend behavioral coverage

**Status:** blocked. **Expected:** focused scenario, guardrail, status, metric, lifecycle, export, accessibility, language, and workflow suites execute. **Actual:** 41 inherited cases plus 26 Sprint 07 workflow cases are defined in source, but Vite fails before collection with `spawn EPERM` in the managed environment.

### GM-059 - Local product slice completion

**Status:** partial. **Expected:** the full local product slice passes frontend gates and browser QA. **Actual:** Sprint 06.1 root lint and typecheck pass. Next production compilation succeeds before a post-compile `spawn EPERM`; the Python suite again exposes nine temp-dependent setup errors before other cases progress. Frontend collection, completed build, dev server, browser QA, and full verification remain blocked. No evidence-backed Scenario Lab defect was reproduced.

## Scenario Lab gates

### GM-060 - Scenario duplication

**Status:** partial. **Expected:** duplicate has a new ID, copied values and valid overrides, distinct name, and no copied result evidence. **Actual:** pure scenario state and workspace integration implement this behavior; targeted TypeScript/ESLint pass and tests are authored, but Vitest execution is blocked.

### GM-061 - Scenario result invalidation

**Status:** partial. **Expected:** editing a scenario clears stale result evidence without clearing unrelated configuration. **Actual:** all baseline/scenario/settings/guardrail edits invalidate comparison evidence while preserving configuration; behavioral execution is blocked.

### GM-062 - Confidence interval rendering

**Status:** partial. **Expected:** exact lower, mean, upper, confidence level, method, and reliability state render. **Actual:** the interval component reads these supplied fields and exposes textual/visual evidence; fixture coverage is authored, but not executed.

### GM-063 - Improvement probability rendering

**Status:** partial. **Expected:** improved, degraded, and tied values reconcile and have textual equivalents. **Actual:** returned values and counts render in a CSS proportion bar plus text; no frontend statistic is recalculated, and execution is blocked.

### GM-064 - Resource comparison rendering

**Status:** partial. **Expected:** baseline/scenario utilization and wait evidence render with correct units and neutral interpretation. **Actual:** the resource-by-pool view includes utilization, supplied delta, idle proportion, wait, concurrent usage, and request count with neutral copy; browser execution is blocked.

### GM-065 - Scenario Lab export

**Status:** partial. **Expected:** JSON/CSV contain expected evidence and exclude full events and unsafe fields. **Actual:** recursive sanitization, versioned JSON, stable CSV headers/rows, and print sections are implemented with focused tests; Vitest and browser download checks are blocked.

### GM-066 - Scenario Lab responsive layout

**Status:** partial. **Expected:** critical controls and analysis remain usable at 390×844, 768×1024, and 1440×900. **Actual:** CSS supplies desktop/two-column, tablet/stacked, and mobile metric-card layouts; viewport execution is blocked because Next dev cannot spawn.

### GM-067 - Scenario Lab accessibility

**Status:** partial. **Expected:** keyboard, label, table, error, visual-equivalent, focus, and live-region behavior pass focused checks. **Actual:** semantic implementation and tests are present and statically reviewed; browser and Vitest execution are blocked.

### GM-068 - Scenario Lab language restrictions

**Status:** partial. **Expected:** generated product output contains none of the prohibited prescriptive phrases. **Actual:** rendered product copy was statically scanned and a case-insensitive UI assertion is authored; the executable assertion is blocked.

## Controlled workflow visualization gates

### GM-069 - Canonical workflow mapping

**Status:** passed by focused runtime check. **Expected:** exact source, stages, routes, resources, terminal states, and rework relationship. **Actual:** the typed mapper executed against the canonical JSON and returned the exact ordered 10 node IDs, seven edge IDs, four resource-link IDs, completion terminal, and rework edge. TypeScript and lint also pass; Vitest remains blocked separately.

### GM-070 - Deterministic layout

**Status:** passed by focused runtime check. **Expected:** the same model produces identical node positions and edge paths. **Actual:** two executed mappings were exactly equal and the canonical quality-check position matched row 3, column 2. Browser layout QA remains separate and blocked.

### GM-071 - Baseline immutability

**Status:** passed by focused runtime check. **Expected:** creating the presentation model does not mutate the operational model. **Actual:** canonical JSON serialization was byte-equivalent before and after executed mapping. The authored Vitest assertion remains uncollected due the environment.

### GM-072 - Scenario-change overlay

**Status:** partial. **Expected:** controlled overrides mark only the intended source, stage, route, resource, or SLA evidence. **Actual:** mapping uses explicit overrides, supports every target kind, and warns for unknown targets. Pure and component assertions are authored but blocked at test startup.

### GM-073 - Pressure-overlay scaling

**Status:** passed by focused runtime check. **Expected:** known finite metric values produce exact normalized presentation values from 0 to 1. **Actual:** the pure scaler executed exact minimum `0`, midpoint `0.5`, and maximum `1` cases successfully.

### GM-074 - Equal-value overlay

**Status:** passed by focused runtime check. **Expected:** equal finite values receive neutral equal display intensity. **Actual:** the executed scaler returned `0.5` for both equal values exactly.

### GM-075 - Missing-evidence behavior

**Status:** partial. **Expected:** missing stage or resource values render unavailable and never become zero. **Actual:** the executed scaler preserved `null`, `NaN`, and infinity as `null`, while the typechecked UI labels null evidence unavailable. Render execution remains blocked.

### GM-076 - Entity selection

**Status:** partial. **Expected:** selecting a source, stage, resource, or terminal shows its correct structural and returned evidence. **Actual:** one-selection state and kind-specific inspector content are implemented with close/focus restoration assertions; browser and Vitest execution are blocked.

### GM-077 - Baseline-versus-scenario evidence

**Status:** partial. **Expected:** a controlled fixture renders exact baseline, scenario, and backend-supplied delta values. **Actual:** the fixture now includes stage and resource aggregates, and comparison inspection reads supplied utilization delta without deriving missing stage deltas. Execution is blocked.

### GM-078 - Accessible textual flow

**Status:** partial. **Expected:** the complete canonical workflow, relationships, resource assignments, scenario changes, and selected overlay values are represented in semantic text. **Actual:** semantic entity and relationship lists plus a visible list/table mode are implemented and asserted; assistive-technology and Vitest execution are blocked.

### GM-079 - Responsive flow

**Status:** partial. **Expected:** desktop, tablet, and mobile use the intended map, inspector, and ordered fallback at 1440×900, 768×1024, and 390×844. **Actual:** controlled grid, stacked inspector, hidden mobile connectors, and vertical node order are defined in CSS; `next dev` cannot spawn, so viewport QA is blocked.

### GM-080 - Visualization language restrictions

**Status:** partial. **Expected:** visualization and inspector output contain no prohibited advisory, causal, or definitive-constraint language. **Actual:** a case-insensitive static scan of workflow output source is clean and a rendered-output assertion is present; executable DOM assertion remains blocked.

## Sprint 08 golden models — GM-081 through GM-099

- **GM-081 — Sensitivity target validation:** known registered target passes; unknown entity and unsupported field fail safely.
- **GM-082 — Tested-value materialization:** every value changes only the requested scalar and validates the full model.
- **GM-083 — Baseline immutability:** canonical baseline serialization and hash remain unchanged.
- **GM-084 — Canonical value ordering:** distinct request values execute and return in ascending numeric order while original order is retained.
- **GM-085 — Shared seed schedule:** every value at a run index uses the same derived seed.
- **GM-086 — Baseline execution reuse:** the baseline value executes exactly once per run index.
- **GM-087 — Per-value aggregation:** selected metric means, dispersion, quantiles, and confidence evidence reconcile to successful scalar snapshots.
- **GM-088 — Paired sensitivity deltas:** absolute, relative, improvement, degradation, and tie evidence reuse comparison formulas.
- **GM-089 — Adjacent finite differences:** only adjacent successful points produce differences.
- **GM-090 — Normal elasticity:** finite non-zero baseline inputs produce the documented normalized ratio.
- **GM-091 — Elasticity null rules:** baseline, zero baseline parameter/metric, zero parameter change, and non-finite inputs return null.
- **GM-092 — Observed monotonicity:** increasing, decreasing, flat, tolerance, mixed, and insufficient evidence classify deterministically.
- **GM-093 — Threshold crossing:** upward/downward, exact threshold, no crossing, and failed-point interruption use adjacent intervals only.
- **GM-094 — Failed-value isolation:** a non-baseline execution failure cannot contaminate other values; baseline failure invalidates the request.
- **GM-095 — Sensitivity work budget:** `items × runs × values` above 100,000 fails before simulation.
- **GM-096 — Sensitivity reproducibility:** identical requests produce identical canonical results.
- **GM-097 — Event-retention policy:** ordinary executions use summary detail and return zero retained events.
- **GM-098 — Sensitivity payload:** smoke/full benchmark output records payload bytes against the existing internal product threshold.
- **GM-099 — Sensitivity language restrictions:** UI, API, CLI, and docs contain no optimum or recommendation claim.

## Sprint 09 golden models — GM-100 through GM-121

- **GM-100 — Economic assumption validation:** valid assumptions pass; negative, duplicate, unknown-entity, invalid-currency, and invalid-amortization inputs fail before simulation.
- **GM-101 — Resource provisioning cost:** known capacity, measurement duration, and rate produce the exact component; utilization is never an operand.
- **GM-102 — Stage visit cost:** known visit count and rate produce the exact component.
- **GM-103 — Queue holding cost:** known time-weighted queue, measurement duration, and rate produce the exact global or stage component.
- **GM-104 — SLA violation cost:** known terminal population and attainment produce the exact violation count and cost.
- **GM-105 — Failure and rework cost:** controlled terminal-failure and global/stage rework counts produce exact components.
- **GM-106 — Recurring cost total:** every configured available component sums exactly to the recurring operating total; unconfigured placeholders add zero.
- **GM-107 — Cost per completed item:** the total divided by completed count is exact and zero completions return null.
- **GM-108 — Missing configured evidence:** a missing required source is unavailable and invalidates the total rather than becoming zero.
- **GM-109 — Paired cost deltas:** controlled same-index baseline/scenario snapshots produce exact absolute, relative, and component deltas.
- **GM-110 — Cost probabilities:** lower, higher, and tied counts and probabilities reconcile to the paired economic intersection.
- **GM-111 — One-time cost separation:** intervention cost remains separate when no amortization period is supplied.
- **GM-112 — Intervention amortization:** one-time cost divided by an explicit positive period count produces exact amortized and combined per-period evidence.
- **GM-113 — Trade-off classification:** every documented cost/objective/flat classification follows direction-aware paired mean deltas and tolerances.
- **GM-114 — Incremental cost per improvement:** direction-aware improvement produces the exact ratio; no/flat/degraded/missing inputs return null and negative valid values remain.
- **GM-115 — Economic guardrail:** configured recurring, per-completion, increase, and amortized thresholds return independent exact evidence without changing operational rank.
- **GM-116 — Economic sensitivity:** the existing 0.6.0 sweep yields cost aggregates, paired deltas, finite differences, monotonicity, and threshold crossings without a second sweep.
- **GM-117 — Economic reproducibility:** identical requests produce identical canonical results apart from explicitly measured evaluation timing.
- **GM-118 — Economic work budget:** existing comparison and sensitivity formulas and the 100,000-unit limit remain unchanged.
- **GM-119 — Economic event retention:** every ordinary observed run is summary-only with zero included and retained events.
- **GM-120 — Economic payload:** canonical Scenario Lab and benchmark responses record bytes against the existing internal product threshold.
- **GM-121 — Economic language restrictions:** API, CLI, UI, exports, and evidence contain no ROI, profit, guarantee, optimum, or prescriptive intervention claim.

Focused evidence lives in `test_sensitivity_models.py`, `test_sensitivity_materializer.py`, `test_sensitivity_analytics.py`, `test_sensitivity_coordinator.py`, `test_sensitivity_api.py`, `test_sensitivity_cli.py`, and `test_sensitivity_benchmark.py`. Frontend adapter and panel cases live in `sensitivity-core.test.ts` and `sensitivity-panel.test.tsx`; environment-blocked collection must be reported as blocked, never passed.

## Sprint 09.1 frontend verification inventory

`apps/web/tests/` contains 17 files (11 pre-existing plus 6 new playback files) and approximately 68 pre-existing cases plus roughly 60 new playback cases (unit and component). Unit-only files (no DOM rendering): `playback-normalize.test.ts`, `playback-timeline.test.ts`, `playback-controller.test.ts`, `playback-journey.test.ts`, `playback-important-events.test.ts`, `playback-export.test.ts`. Component (jsdom + Testing Library) files include `playback-panel.test.tsx` alongside the pre-existing `workflow-visualization.test.tsx`, `workspace-scenario-lab.test.tsx`, `sensitivity-panel.test.tsx`, and `economics-panel.test.tsx`. Native dependency: `jsdom` for component tests; none for the unit-only playback files. No test in this repository is browser-only (all run under Vitest/jsdom). Vitest cases must not be marked passed unless actually executed and observed passing in that session; see the Sprint 09.1/10 session record for the exact executed/blocked status encountered.

## Sprint 10 golden models — GM-122 through GM-140

- **GM-122 — Representative source validation:** `extractRepresentativeSource` returns a complete `PlaybackSource` for a valid `RepresentativeVariantResult` and `null` when the representative, its result, or its events are absent. **Automated by:** `playback-normalize.test.ts`.
- **GM-123 — Event ordering:** normalized events sort by `simulationTime` then original source index; equal timestamps preserve source order. **Automated by:** `playback-normalize.test.ts`, `playback-timeline.test.ts`.
- **GM-124 — Arrival and queue reconstruction:** controlled `ITEM_CREATED`/`QUEUE_ENTERED` events produce exact stage waiting counts. **Automated by:** `playback-timeline.test.ts`.
- **GM-125 — Processing reconstruction:** controlled `PROCESS_STARTED`/`PROCESS_COMPLETED` events produce exact processing counts. **Automated by:** `playback-timeline.test.ts`.
- **GM-126 — Resource reconstruction:** controlled `PROCESS_STARTED`/`RESOURCE_RELEASED` events produce exact busy counts against configured capacity. **Automated by:** `playback-timeline.test.ts`, `playback-important-events.test.ts`.
- **GM-127 — Route reconstruction:** a controlled `ROUTE_SELECTED` event is visible in `eventsAtTime` with the correct `routeId`/`targetId`. **Automated by:** `playback-timeline.test.ts`.
- **GM-128 — Rework reconstruction:** a repeated stage visit after `ITEM_REWORKED` remains a distinct, correctly ordered visit. **Automated by:** `playback-timeline.test.ts`, `playback-journey.test.ts`.
- **GM-129 — Completion and failure:** controlled sampled items reach exact `completed`/`failed` terminal sets. **Automated by:** `playback-timeline.test.ts`.
- **GM-130 — Item journey:** a controlled event history produces the exact visit list, route decisions, cycle time, and SLA result. **Automated by:** `playback-journey.test.ts`.
- **GM-131 — Seek determinism:** `buildFrame(timeline, t)` called twice at the same `t` returns an equal frame. **Automated by:** `playback-timeline.test.ts`.
- **GM-132 — Step reversibility:** stepping forward then backward across an interior checkpoint returns to the exact prior index. **Automated by:** `playback-controller.test.ts`, `playback-timeline.test.ts`.
- **GM-133 — Source-switch reset:** switching the representative source resets the controller to the initial (`-1`) checkpoint and pauses. **Automated by:** `playback-panel.test.tsx` (effect on `activeSource` change) and the `restart` action in `playback-controller.test.ts`.
- **GM-134 — Representative identity disclosure:** paired (equal run index and seed) versus separately selected representatives render the correct exact wording. **Automated by:** `playback-panel.test.tsx`.
- **GM-135 — Aggregate/playback separation:** the fixed representative-playback disclaimer and the "Aggregate evidence across successful runs" label remain distinct and no aggregate confidence value renders on the playback timeline. **Automated by:** `playback-panel.test.tsx`.
- **GM-136 — Reduced-motion behavior:** `prefers-reduced-motion` suppresses the automatic playback timer while preserving step/seek and all rendered information. **Reviewed in:** `playback-panel.tsx` (`reducedMotion` gate on the timer effect); executable jsdom `matchMedia` mocking is deferred to when Vitest execution is unblocked.
- **GM-137 — Event-ledger equivalence:** the ledger table exposes every essential field (time, item, event, stage, resource, details) with a caption and proper headers. **Automated by:** `playback-panel.test.tsx`.
- **GM-138 — Playback payload boundary:** presentation/export byte sizes are recorded by `pnpm benchmark:playback` against the existing internal product threshold. **Recorded in:** `docs/PLAYBACK_PERFORMANCE.md`.
- **GM-139 — Playback export safety:** the export payload contains required evidence fields and excludes filesystem paths, stack traces, and browser/timer/React internals. **Automated by:** `playback-export.test.ts`.
- **GM-140 — Playback language restriction:** rendered playback copy contains none of the restricted causal/recommendation/guarantee/unjustified-typicality phrases. **Automated by:** `playback-panel.test.tsx`.

Focused evidence lives in `apps/web/tests/playback-normalize.test.ts`, `playback-timeline.test.ts`, `playback-controller.test.ts`, `playback-journey.test.ts`, `playback-important-events.test.ts`, `playback-export.test.ts`, and `playback-panel.test.tsx`. `pnpm benchmark:playback` (`scripts/benchmark-playback.mjs`) records `docs/PLAYBACK_PERFORMANCE.md`. Environment-blocked Vitest collection must be reported as blocked, never passed.

## Sprint 11 reconciliation — GM-051, GM-053–080, GM-100–121, GM-122–140

On 2026-07-20, on a macOS host with Node 22.22.3/pnpm 11.7.0/Python 3.12.13, the environment blocker recorded against every prior sprint (Vite/Vitest child-process startup, `next dev`/`next build` child processes, Python isolated build environments) did not reproduce. `pnpm verify` passed completely for the first time in this project's history: ruff, ESLint, mypy (51 files), `tsc --noEmit`, the full backend pytest suite (247/247), the full Vitest suite (18/18 files, 140/140 tests), both production builds, the canonical CLI example, all six benchmark smokes, and deterministic source packaging. A real Vercel Services deployment (`https://ops-twin.vercel.app`) was also built, inspected, and exercised live in the in-app browser (see `docs/sprints/SPRINT_11_RUNTIME_AND_FLAGSHIP_POLISH.md` for the full record). This section reconciles every previously blocked/partial gate in the ranges the sprint scoped for reconciliation against that evidence. "Browser-confirmed" means the behavior was directly observed against the deployed production app in this session, not inferred from source or tests alone.

- **GM-051 — Vercel Services deployment:** **Pass.** One project, two services, one domain; `/`, `/workspace`, `/api/simulation/health` and six analysis endpoints returned correct evidence; ADR-014 accepted below.
- **GM-053 — Scenario result statuses:** Pass. `scenario-lab-core.test.ts` ("metric presentation and statuses") and `workspace-scenario-lab.test.tsx` execute and pass; browser-confirmed ranked/unranked status text in the Overview tab.
- **GM-054 — Optional guardrail control:** Pass. `scenario-lab-core.test.ts` ("optional guardrail mapping", 5 cases) and `workspace-scenario-lab.test.tsx` ("omits a disabled guardrail...") pass.
- **GM-055 — Risk comparison presentation:** Pass. Browser-confirmed the Risk tab renders threshold, violation percentages, and four transition counts from returned evidence; `workspace-scenario-lab.test.tsx` ("renders confidence, probability, risk, resource...") passes.
- **GM-056 — Request lifecycle:** Pass. `api-lifecycle.test.ts` (abort, timeout, malformed JSON, network failure — 4 cases) passes.
- **GM-057 — Result accessibility:** Pass. `workspace-scenario-lab.test.tsx` ("uses accessible table headers...") passes; browser-confirmed zero unlabeled buttons/inputs, zero positive `tabindex`, and a `aria-live="polite"` result announcement.
- **GM-058 — Frontend behavioral coverage:** Pass. The current full suite (18 files, 140 tests) executes and passes; the case count differs from the sprint-07-era "41 + 26" figure because later sprints added playback/economics/sensitivity coverage.
- **GM-059 — Local product slice completion:** Pass. `pnpm verify` passes end to end; browser QA completed the full product journey against the deployed app with no console or network errors.
- **GM-060 — Scenario duplication:** Pass. `scenario-lab-core.test.ts` ("duplicates configuration under a new stable identity...") passes.
- **GM-061 — Scenario result invalidation:** Pass. `workspace-scenario-lab.test.tsx` ("invalidates stale evidence after a scenario edit") passes.
- **GM-062 — Confidence interval rendering:** Pass. Browser-confirmed exact lower/mean/upper, confidence level, and "Reliable sample size" text in the Overview tab.
- **GM-063 — Improvement probability rendering:** Pass. Browser-confirmed improved/degraded/tied percentages and run counts.
- **GM-064 — Resource comparison rendering:** Pass. Browser-confirmed utilization, delta, wait, and concurrent-usage evidence in the Resources tab.
- **GM-065 — Scenario Lab export:** Pass. `scenario-lab-exports.test.ts` (4 cases) passes; browser-confirmed live JSON (223,229 bytes) and CSV (469 bytes) blob downloads for both the comparison and economics panels.
- **GM-066 — Scenario Lab responsive layout:** Pass. Browser-confirmed no page-level horizontal overflow at 390×844, 768×1024, and 1440×900; wide tables/tab strips use a contained `overflow-x: auto` wrapper instead.
- **GM-067 — Scenario Lab accessibility:** Pass. Browser-confirmed as in GM-057; table captions, a labelled range slider (`aria-valuetext`), and keyboard-operable controls were all observed present.
- **GM-068 — Scenario Lab language restrictions:** Pass. `workspace-scenario-lab.test.tsx` ("keeps generated product output free of prescriptive language") passes; browser-confirmed factual (non-prescriptive) economics trade-off wording.
- **GM-069 through GM-071 — Canonical mapping, deterministic layout, baseline immutability:** Pass. `workflow-presentation.test.ts` executes and passes (previously verified only by a one-off focused script run).
- **GM-072 — Scenario-change overlay:** Pass. `workflow-presentation.test.ts` (6 scenario-change-mapping cases) and `workflow-visualization.test.tsx` ("shows explicit scenario changes before execution") pass.
- **GM-073 through GM-075 — Overlay scaling and missing-evidence behavior:** Pass. `workflow-presentation.test.ts` ("workflow overlay scaling", 4 cases) passes.
- **GM-076 — Entity selection:** Pass. `workflow-visualization.test.tsx` ("selects a stage and closes its inspector") passes; browser-confirmed via the Flow entity buttons.
- **GM-077 — Baseline-versus-scenario evidence:** Pass. `workflow-visualization.test.tsx` ("renders supplied baseline, scenario, and resource delta evidence") passes.
- **GM-078 — Accessible textual flow:** Pass. `workflow-visualization.test.tsx` ("provides a visible list mode...") passes; browser-confirmed the "Workflow entities"/"Workflow relationships" semantic lists and "View as list" toggle.
- **GM-079 — Responsive flow:** Pass. Covered by the GM-066 browser measurement (the Flow section is part of the same page).
- **GM-080 — Visualization language restrictions:** Pass. `workflow-visualization.test.tsx` ("avoids restricted product language") passes.
- **GM-100 through GM-121 — Economics evaluator, comparison, and sensitivity behavior:** Pass. All backend economics tests (`test_economic_evaluator.py`, `test_economic_comparison.py`, `test_economic_delivery.py` schema-parity, `test_economic_sensitivity.py`, including the new observer-failure regression test) are part of the 247/247 passing backend suite; `economics-core.test.ts` and `economics-panel.test.tsx` pass; browser-confirmed a live economics run (blank-vs-zero distinction, negative-input rejection with a `role="alert"` message, separate one-time-cost evidence, factual trade-off wording, JSON/CSV export).
- **GM-122 through GM-135, GM-137, GM-139, GM-140 — Playback normalization, timeline, controller, journey, export, ledger, disclosure, and language:** Pass. Every named test file (`playback-normalize.test.ts`, `playback-timeline.test.ts`, `playback-controller.test.ts`, `playback-journey.test.ts`, `playback-important-events.test.ts`, `playback-export.test.ts`, `playback-panel.test.tsx`) executes and passes; browser-confirmed live source-toggle switching (run index 44 → 38 on a different seed), restart/step/seek/speed/important-event navigation, a 542-row captioned event ledger, and the item journey inspector against the deployed representative run.
- **GM-136 — Reduced-motion behavior:** Partial. The `reducedMotion` gate on the playback timer effect is unchanged and source-reviewed; `window.matchMedia('(prefers-reduced-motion: reduce)').matches` was confirmed `false` in the browser QA session (the default, since no reduced-motion preference was set), but no automated `matchMedia`-mocked test or manual reduced-motion-preference browser run was executed this sprint, so the gate itself remains unverified at runtime.
- **GM-138 — Playback payload boundary:** Deferred. Unchanged this sprint; still recorded only in `docs/PLAYBACK_PERFORMANCE.md` from Sprint 10.
