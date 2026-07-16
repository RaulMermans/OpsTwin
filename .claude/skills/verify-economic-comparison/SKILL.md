---
name: verify-economic-comparison
description: Verify OpsTwin 0.7.0 explicit-assumption recurring-cost comparison and economic sensitivity evidence locally.
---

# Verify economic comparison

1. Read `CLAUDE.md`, `docs/ECONOMIC_MODEL_SPEC.md`, `docs/ECONOMIC_COMPARISON_SPEC.md`, and `docs/VALIDATION_PLAN.md`.
2. Inspect only `app/domain/economics.py`, `app/economics/`, economic contracts, routes, CLI branches, UI economics files, tests, examples, and benchmarks.
3. Verify finite non-negative assumptions, currency/time/entity/duplicate validation, every registry formula, configured-missing versus unconfigured behavior, recurring reconciliation, and null cost per completion.
4. Verify same-run scalar capture, shared seeds, paired intersections/deltas/probabilities, zero event retention, and unchanged work budgets.
5. Verify one-time separation, explicit amortization, trade-off labels, incremental-cost null rules, economic guardrails, and unchanged operational ranking.
6. Verify economic sensitivity invokes the 0.6.0 coordinator once and preserves failed points, finite differences, monotonicity, crossings, and baseline zero paired delta.
7. Scan runtime strings and exports for prescriptive, ROI, profit, guarantee, secret, path, browser-state, and event evidence.
8. Run focused checks serially. Report temp-directory or child-process sandbox blockers exactly; never disable checks, change permissions, delete inaccessible directories, add workers, or convert blocked evidence into a pass.
