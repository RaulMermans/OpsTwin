# Sprint 06 - Scenario Lab UX and Visual Analysis

## Objective

Turn the support-operations workspace into a local Scenario Lab where users can organize up to three scenarios and inspect backend-owned paired comparison evidence across service, flow, risk, and resource outcomes. The product presents evidence and ranking under the selected objective; it does not prescribe an action or add simulation mathematics.

## Environment blocker

The managed Windows workspace still denies access to pip build-tracker and installation temporary directories. The one permitted Sprint 06 attempts reproduced the inherited failures: `pnpm bootstrap` could not write a pip build tracker, and `pnpm verify` could not obtain a child-process exit status in the Node portability check. The directories are preserved, permissions are unchanged, escalation is not repeated, and targeted checks remain the verification path.

## Current product baseline

The local product has a Next.js workspace, a same-origin runtime-checked client, guided support scenarios, and a FastAPI/SimPy comparison service using the accepted `0.5.0` contracts. The backend already owns paired deltas, confidence intervals, improvement probabilities, risks, guardrails, eligibility, ranking, representatives, failures, hashes, and integrity.

## Carried-forward Sprint 05.1 gaps

- Complete factual scenario statuses, including failure and ineligibility.
- Add one optional contract-supported guardrail without inventing evaluation logic.
- Expose paired risk and resource comparison evidence.
- Distinguish abort, timeout, retry, stale response, and unexpected response states.
- Expand frontend behavioral and accessibility coverage.

## In scope

- Scenario Lab information architecture and scenario collection management.
- Central metric presentation metadata and response adapters.
- Overview, metrics, uncertainty, risk, resources, and technical evidence views.
- Optional guardrail request mapping and backend result presentation.
- JSON/CSV client exports and print styling.
- Request lifecycle, accessibility, responsive refinement, tests, and documentation.

## Out of scope

No contract or simulation formula changes, topology editing, charting/animation dependency, persistence, authentication, cloud projects, server exports, cost modelling, optimization, recommendation engine, parallel execution, remote action, or deployment.

## Information architecture

`/workspace` presents a Scenario Lab with a configuration column containing Baseline, Scenario set, and Execution settings. Successful comparison evidence appears in an Analysis region with keyboard-operable Overview, Metrics, Risk, Resources, and Technical evidence views. Configuration remains available after success or failure; mobile uses one stacked reading order.

## Scenario-management behavior

Scenario names are non-empty and editable without changing IDs or overrides. Duplicate creates a new session-stable ID, copies valid configuration, creates a distinct name, and has no result evidence. Delete affects only the selected scenario and restores focus to the nearest logical card or add control. Move-up and move-down change display order only. Any material edit invalidates stale comparison evidence while preserving configuration and the immutable baseline.

## Visualization principles

All figures are supplied by the backend. Missing and non-finite evidence is unavailable, never zero-filled. Percentages, durations, units, precision, direction copy, and visualization suitability come from a central presentation registry. Confidence intervals show lower, mean, upper, confidence level, method, and reliability without significance language. Probability bars and risk transitions always have textual equivalents. Utilization is contextual and neutral.

## Accessibility requirements

Controls have programmatic labels, units, described errors, `aria-invalid`, explicit scenario action names, visible focus, and keyboard operation. Loading, completion, and errors use live regions. Analysis tabs follow tab semantics. Tables have captions and scoped headers. Status, confidence, probability, and risk evidence never depend on colour. Focus moves logically after scenario deletion and request completion or failure.

## Export behavior

The browser may download a sanitized versioned JSON artifact and a flat CSV scenario summary from current returned evidence. Exports exclude filesystem paths, browser state, stack traces, secrets, and full event logs. Print CSS produces a readable product, baseline, ranking, scenario, risk, and execution summary; application code does not generate PDFs.

## Test plan

Focused Vitest coverage exercises scenario rename/duplicate/delete/order/invalidation; guardrail omission/mapping/validation/copy; status mapping; metric formatting and uncertainty; risk/resource evidence; abort/timeout/retry/stale protection; sanitized JSON/CSV exports; semantic labels, live regions, tables, keyboard controls, and prohibited-language scans. Existing backend tests remain authoritative for mathematics.

## Verification limitations

Full bootstrap and verification are blocked by the managed sandbox and must not be reported as passing. Available package-level lint, typecheck, web tests, and production build will be run directly. Local browser QA will be attempted only if the existing services can run without permission changes. Static checks are reported separately from executed commands.

## Acceptance criteria

The implementation satisfies AC1-AC11 in the Sprint 06 work package: stable scenario management; factual overview; safe metric/uncertainty/risk/resource evidence; backend-owned guardrails/statuses; sanitized local exports; robust request lifecycle; accessible responsive layouts; focused tests and honest verification; and no Git, remote, or Vercel operation.

## Definition of done

Scenario management, analysis sections, guardrail control, exports, lifecycle states, accessibility, responsive layouts, GM-060-GM-068 documentation, focused frontend tests, targeted gates, browser QA where possible, static Vercel review, hygiene scans, scratchpad update, and an evidence-separated final report are complete. Blocked gates remain explicitly blocked.

## Rollback plan

Preserve the existing contracts and backend. If the integrated workspace becomes unstable, retain the last functioning configuration flow, separate scenario management from analysis, and reintroduce analysis sections one at a time through response adapters. Do not remove error/accessibility behavior, alter permissions, delete inaccessible directories, or use destructive Git operations.
