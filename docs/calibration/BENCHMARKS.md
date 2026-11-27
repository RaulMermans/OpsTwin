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

Naive baseline: approved 30-minute processing and capacity 1, still using estimated arrivals.

CI: `pnpm benchmark:calibration-smoke` (seed 21). Deeper: `pnpm benchmark:calibration`.

Circular evaluation: recovering parameters from this generator shows consistency of the estimator with the laboratory process, not real-world validity.
