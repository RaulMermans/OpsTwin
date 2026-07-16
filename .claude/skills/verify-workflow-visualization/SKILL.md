---
name: verify-workflow-visualization
description: Verify OpsTwin's deterministic read-only Flow mapping, explicit changes, evidence overlays, inspector, accessibility, and responsive fallback without changing backend contracts.
---

# Verify workflow visualization

1. Read `CLAUDE.md`, `docs/WORKFLOW_VISUALIZATION_SPEC.md`, and GM-069 through GM-080 in `docs/VALIDATION_PLAN.md`.
2. Inspect only workflow components, workflow library modules, their integration/imports, CSS, fixtures, and focused tests.
3. Verify stable unique IDs, canonical nodes/edges/resources/terminal/rework, deterministic positions/paths, input immutability, safe unknown-reference handling, and no presentation metadata in requests.
4. Verify explicit override targeting, raw backend stage/resource values, supplied deltas only, exact display scaling, missing/equal evidence, and prohibited product language.
5. Verify semantic relationship/list equivalents, keyboard node selection, inspector close/focus behavior, non-colour signals, and desktop/tablet/mobile CSS.
6. Run available focused tests, typecheck, lint, build, and browser viewports. If runtime startup is environment-blocked, report it accurately and do not convert static review into a pass.
