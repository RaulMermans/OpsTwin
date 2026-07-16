---
name: verify-simulation
description: Verify OpsTwin simulation behavior against specifications and golden models; use for simulation reviews, not implementation or automatic fixes.
---

# Verify simulation

1. Read `CLAUDE.md`, the relevant simulation/repeated/scenario specification, `docs/METRIC_DEFINITIONS.md`, and `docs/VALIDATION_PLAN.md`.
2. Inspect only relevant domain, engine/scenario, contracts, CLI, example, and test files.
3. Run the relevant golden-model tests. For scenario comparison, run GM-030 through GM-041 and verify baseline immutability, paired seeds and deltas, failure isolation, ranking eligibility, and at-most-two event-rich representatives.
4. Compare output with documented exact results, including failure accounting and bounded retention.
5. Report passes, failures, formula mismatches, reproducibility problems, retention regressions, and missing tests.

Do not change code unless explicitly asked to fix findings.
