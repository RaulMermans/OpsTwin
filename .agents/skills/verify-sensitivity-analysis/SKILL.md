---
name: verify-sensitivity-analysis
description: Verify the local OpsTwin one-factor-at-a-time sensitivity slice and report executable evidence without changing permissions or cleaning inaccessible directories.
---

# Verify sensitivity analysis

1. Read `docs/SENSITIVITY_ANALYSIS_SPEC.md` and `docs/VALIDATION_PLAN.md`.
2. Inspect only sensitivity contracts, backend modules, UI adapters/component, and their focused tests.
3. Run focused sensitivity pytest modules once with the existing environment.
4. Verify registered target behavior, baseline immutability and inclusion, canonical ordering, seed pairing, paired deltas, finite differences, elasticity nulls, monotonicity, adjacent thresholds, work limits, event retention, API, CLI, payload size, and restricted language.
5. Run the sensitivity smoke benchmark once. Run the full benchmark only when explicitly required.
6. Run relevant typecheck/lint commands once. If the sandbox blocks process creation or temp directories, record the exact blocker and continue with source/static evidence.
7. Never change permissions, delete inaccessible directories, weaken checks, stage or commit files, use remotes, or deploy.
8. Report pass, fail, and blocked gates separately; do not claim blocked evidence passed.
