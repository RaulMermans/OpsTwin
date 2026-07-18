# OpsTwin contracts

These JSON Schema Draft 2020-12 contracts define implementation-neutral boundaries. Durations use minutes, `schemaVersion` is required, and unexpected fields are rejected where practical.

- `operational-model.schema.json` (`0.2.0`): collection-based seeded operational workflow.
- `simulation-request.schema.json` (`0.3.0`): model, seed/run-label overrides, observation window, and result detail.
- `simulation-result.schema.json` (`0.3.0`): shared internal, API, and CLI result with observation metadata, time-weighted metrics, integrity, detail counts, and selected canonical events.
- `repeated-simulation-request.schema.json` (`0.4.0`): one model, deterministic seed schedule, run bounds, confidence level, observation, thresholds, and representative detail.
- `repeated-simulation-result.schema.json` (`0.4.0`): successful/failed accounting, run seeds, aggregate metrics, risks, diagnostics, representative single-run evidence, execution metadata, and aggregate integrity.
- `scenario-comparison-request.schema.json` (`0.5.0`): baseline model, 1–5 bounded scenario definitions, execution policy, objective, guardrails, and representative settings.
- `scenario-comparison-result.schema.json` (`0.5.0`): immutable model hashes, paired deltas and risks, utilization evidence, eligibility, comparative ranking, bounded representatives, work accounting, and integrity.
- `sensitivity-request.schema.json` (`0.6.0`): one registered target, 2–10 explicit unique values including the baseline, bounded paired execution, 1–8 metrics, and optional thresholds.
- `sensitivity-result.schema.json` (`0.6.0`): canonical response points, per-value aggregates and paired deltas, finite differences, observed elasticity, monotonicity, observed threshold intervals, work accounting, and integrity.
- `economic-assumptions.schema.json` (`0.7.0`): explicit currency/time semantics and bounded recurring-cost categories.
- `economic-comparison-request.schema.json` and `economic-comparison-result.schema.json` (`0.7.0`): paired cost capture, intervention separation, factual trade-offs, economic guardrails, isolated/categorized observer-failure evidence, and integrity.
- `economic-sensitivity-request.schema.json` and `economic-sensitivity-result.schema.json` (`0.7.0`): one wrapper around the `0.6.0` sweep with selected cost metrics and discrete response evidence.

JSON Schema validates shapes and numeric bounds. Pydantic additionally validates duplicate IDs, cross-record references, route probability sums, objective direction, guardrail resources, override semantics, sensitivity value uniqueness, target compatibility, explicit baseline inclusion, currencies, economic entity scopes, intervention relationships, and configured categories. Run `pnpm test` or `pnpm verify` to validate examples and actual results.
