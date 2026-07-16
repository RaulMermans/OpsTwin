---
name: verify-deployable-slice
description: Verify the OpsTwin support Scenario Lab, same-origin API, bounded payloads, accessibility, exports, and local evidence without deploying.
---

# Verify deployable slice

1. Read `docs/SCENARIO_LAB_SPEC.md`, `docs/WORKFLOW_VISUALIZATION_SPEC.md`, `docs/PRODUCT_SLICE_SPEC.md`, `docs/VERCEL_DEPLOYMENT.md`, `docs/VERCEL_PREVIEW_EVIDENCE.md`, and GM-042 through GM-080.
2. Attempt `pnpm bootstrap` and `pnpm verify` once. If the managed sandbox reproduces known pip-directory or child-spawn failures, record them, do not retry, and continue with available `pnpm lint`, `pnpm typecheck`, `pnpm test:web`, and `pnpm build` or package-level equivalents.
3. Check relative API paths, sampled evidence, 30,000 UI and 100,000 backend work guards, 1 MB response guard, safe errors, stale-request protection, and zero ordinary retained events.
4. Check scenario rename/duplicate/delete/order and invalidation; optional guardrail omission/mapping; factual statuses; metric units/nulls; supplied confidence/probability/risk/resource evidence; workflow mapping/change/overlay immutability; JSON/CSV sanitization; print sections; labels/live regions/tables/keyboard controls; and prohibited language.
5. Browser-check landing, workspace, Flow modes/list/selection/inspector, scenario actions, guardrail, comparison, all analysis views, exports, abort/failure preservation, 390×844, 768×1024, 1440×900, overflow, hydration, and console errors when local services can start.
6. Review `vercel.json` statically only. Do not log in, link, create, deploy, or promote. Leave ADR-014 proposed and preview validation deferred.
