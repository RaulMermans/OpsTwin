# Validation standard

Temporal split: earlier training fraction (default 70%), later holdout. No shuffled operational records.

Leakage controls: created-timestamp arrivals, worklogs, and transitions for estimation use training only. Thresholds are fields on the request.

Mode: **generative**. The engine samples Poisson arrivals. This does not validate a historical-arrival replay.

Compared when units and populations match: holdout created count vs simulated `createdDuringWindow`; completions; cycle-time median and p90 for cases created and completed in the window.

Not compared: utilization without resource observations; SLA attainment across calendar mismatch.

Outcomes: `passed_for_defined_scope`, `failed`, `inconclusive`, `insufficient_evidence`, `incompatible_metrics`.

Empty initial conditions: backlog at holdout start is recorded and is not injected. Historical accuracy is not claimed for WIP.
