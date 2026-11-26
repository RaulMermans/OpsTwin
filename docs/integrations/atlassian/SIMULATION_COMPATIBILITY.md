# Simulation intervention compatibility

Source: `apps/simulation-api/app/scenarios/registry.py`, materializer topology lock, contracts `0.2.0`/`0.5.0`. No engine rewrite in CG-0.

| Intervention | Mechanism | Classification |
|---|---|---|
| Increase human capacity | `resourcePool.capacity` ≥ 1 | **Existing engine** |
| Reduce triage/resolution duration | stage `processing.*` matching baseline distribution | **Existing engine** |
| Additional human review | extra stage/route | **Major architecture** (topology change rejected) |
| Automation-related rework | `stage.failure.probability`, `maximumReworkAttempts` | **Existing engine** if failure already modeled; else **bounded extension** to add failure config |
| Change routing probabilities | `route.probability` on `routeId:targetId` | **Existing engine** (options must already exist; probabilities must remain valid) |
| Change arrival rates | `source.arrivalInterval` or `meanInterarrivalTime` | **Existing engine** |
| Hybrid human-AI | parameterized capacity + processing + failure + route mix | **Adapter** over existing overrides; not a new entity type |
| Autonomous resolution via new route | new route option / completion edge | **Major architecture** unless the completion edge already exists (then probability only) |
| SLA target change | `slaRule.targetDuration` | **Existing engine** (simulation minutes, not JSM calendars) |

## Engine invariants that adapters must not break

- Baseline is immutable; scenarios are identity overrides (ADR-004, ADR-011).
- Topology (ids, route shapes, queue policies, SLA sources) must match baseline after materialization.
- Paired CRN uses shared child seeds (ADR-012). **Changed routing that consumes extra random draws can desynchronize later streams** even with shared seeds — known limitation, not silently ignored.
- Distributions: fixed, exponential, uniform, triangular only, as already registered.
- Work budgets still apply to comparison/sensitivity/economics coordinators.
- Integrity validators remain the serialization gate.

## Modeling limitations (not engine bugs)

- Jira status dwell ≠ busy handling time.
- Unique assignees ≠ licensed effective capacity.
- Changelog routing is a reconstruction, not ground truth.
- Business-calendar SLA ≠ model `minutes`.
- Historical calibration is an estimator with bias, not identity.
- Future AI effectiveness without a pilot is an **assumption**, shown as missing evidence, never as a measured fact.
