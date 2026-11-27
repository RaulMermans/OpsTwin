# Validation standard

Temporal split: earlier **time** fraction of the snapshot observation window (default 70%), later holdout. Both windows must lie inside the snapshot window. No shuffled operational records. The cut is not chosen from holdout arrival counts.

Leakage controls: created-timestamp arrivals, worklogs, and transitions for estimation use training only. Thresholds are fields on the request. Holdout-only mutations must not change training estimates.

Mode: **generative**. The engine samples Poisson arrivals. This does not validate a historical-arrival replay.

Populations: closed-start/open-end `[start, end)`. Arrival volume = cases/items created in the window. Throughput = completions **of those newly arrived cases** in the window, not total completions including backlog. Cycle times use the same newly-arrived completed set. Unavailable comparable metrics stay unavailable (no fallback to all completed items). Historical completion is reconstructed from lifecycle events, not solely from the case's final current status.

Not compared: utilization without resource observations; SLA attainment across calendar mismatch; total throughput including historical WIP.

Outcomes: `passed_for_defined_scope`, `failed`, `inconclusive`, `insufficient_evidence`, `incompatible_metrics`.

Empty initial conditions: Core starts empty. If historical backlog at holdout start is positive or unknown, throughput and cycle targets are `incompatible_metrics` (`empty_system_arrival_only`). Exploratory simulation may still run without a historical adequacy claim.
