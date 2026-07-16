---
paths:
  - "apps/simulation-api/**/*.py"
  - "apps/simulation-api/pyproject.toml"
---

# Python simulation rules

- Type-annotate functions and public methods.
- Make randomness seedable; never use global random state.
- Separate domain models, execution, and metric calculation.
- Prefer deterministic fixtures and exact values in tests.
- Reject invalid input explicitly and avoid premature abstractions.
- Follow `docs/SIMULATION_SPEC.md`; formulas must match `docs/METRIC_DEFINITIONS.md`.
