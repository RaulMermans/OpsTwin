# OpsTwin simulation API

This package contains the stateless FastAPI service and seeded multi-stage SimPy engine using operational-model `0.2.0`, single-run `0.3.0`, repeated-run `0.4.0`, scenario-comparison `0.5.0`, and sensitivity `0.6.0`. `POST /compare/scenarios` and `python -m app.cli compare <path>` execute bounded paired comparisons; `POST /analyze/sensitivity` and `python -m app.cli sensitivity <request-path>` execute bounded one-factor-at-a-time analysis. Use root pnpm commands for bootstrap, development, examples, all four benchmarks, and quality gates.

Single-run behavior is governed by `docs/SIMULATION_SPEC.md`; repeated behavior by `docs/REPEATED_RUN_SPEC.md`; scenario behavior by `docs/SCENARIO_COMPARISON_SPEC.md`; metrics by `docs/METRIC_DEFINITIONS.md`.
