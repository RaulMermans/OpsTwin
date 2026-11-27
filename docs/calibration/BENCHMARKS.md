# Synthetic calibration benchmarks

Generator: `app.calibration.histories.generate_history`. Ground truth is in `ground_truth()` and is not passed to `calibrate()`.

| Profile | Intent |
|---|---|
| A golden | Poisson 30 min, service 8+12, worklogs, high capacity |
| B observable | Same, worklogs treated as processing |
| C partial | No worklogs; assumptions required |
| D noisy | Incomplete extraction; must refuse |
| E nonstationary | Rate change; homogeneous Poisson refused |
| F misspecified | Extra review status; unsupported topology |
| G mixed | Synthetic and observed-labeled cases; origin unknown |
| H shift | Holdout process differs; validation may fail |

Naive baseline: **estimated arrivals with default 30-minute processing and capacity 1**. Same holdout windows and execution budget as the calibrated model.

Expected behavior is per profile: golden/observable recover arrivals (relative error < 25% when identifiable); noisy/nonstationary/misspecified must refuse; shift may construct but must not be treated as historically adequate if the holdout process changed. Parameter recovery is scored separately from historical adequacy.

CI: `node scripts/tasks.mjs benchmark:calibration-smoke` (seed 21, 8 profiles). Full matrix: seeds 1,2,3 × 8 profiles × 3 simulation replications.

False-confidence rate: share of runs that report `validated_for_defined_scope` on profiles that must refuse or that encode a temporal shift.

## CG-3.1 full matrix (2026-11-27)

Seeds 1, 2, 3 × 8 profiles × 3 simulation replications. Mean runtime 253 ms per profile/seed.

| Profile | Seeds | Arrival recovery | Construction / refusal | Historical adequacy | Notes |
|---|---|---|---|---|---|
| golden | 1–3 | rel err 0.032–0.074 | constructed | 1/3 `validated_for_defined_scope`; 2/3 cycle-time fail | Service rel err ≤ 0.045 |
| observable | 1–3 | same | constructed | same split as golden | Worklog service recovery |
| partial | 1–3 | same | constructed via assumptions | same split | Service not empirical |
| noisy | 1–3 | n/a | refuse `insufficient_evidence` | none | Incomplete extraction |
| nonstationary | 1–3 | n/a | refuse `statistical_estimation_failure` | none | Homogeneous Poisson rejected |
| misspecified | 1–3 | n/a | refuse `unsupported_topology` | none | Review path |
| mixed | 1–3 | rel err 0.032–0.074 | constructed | 1/3 validated | Origin remains `unknown` |
| shift | 1–3 | training rate recovered | constructed | 3/3 `historical_validation_failure` | No false confidence |

Naive baseline (estimated arrivals + 30 min service + capacity 1): holdout `failed` on all comparable constructed runs. False-confidence count: 0 / 24. Incorrect refusal count: 0 / 24.

Circular evaluation: recovering parameters from this generator shows consistency of the estimator with the laboratory process, not real-world validity.
