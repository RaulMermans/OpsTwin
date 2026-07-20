# Sprint 11 — Vercel Production Recovery, Runtime Verification, and Flagship Product Polish

## Objective

Recover the failing production Vercel deployment, verify the complete deployed product (routes, API, browser journey, playback, economics, viewports, accessibility), and apply only evidence-backed polish found during that verification. No new analytical capability was added.

## Starting deployment failure

The `ops-twin` Vercel project's production deployment at commit `fd1c3f4` failed during `next build`:

```text
Module not found: Can't resolve '../../../../examples/product/support-operations-baseline.json'
```

## Root cause

`.vercelignore` excludes `examples/` from the deployed bundle (dev tooling only). `apps/web/lib/templates/support.ts` imported a runtime JSON asset from that excluded path, so Turbopack could not resolve it once Vercel stripped `examples/` before compiling the web service. This was a repository packaging defect, not a Vercel infrastructure defect.

## Hotfix

- Added `apps/web/lib/templates/support-operations-baseline.json`, an exact semantic copy of `examples/product/support-operations-baseline.json`, so the web service owns its runtime asset inside the directory `.vercelignore` never excludes.
- Changed `support.ts`'s import from `../../../../examples/product/support-operations-baseline.json` to `./support-operations-baseline.json`.
- Kept the original canonical example untouched; backend tests, examples, CLI evidence, and documentation still depend on it.
- Added `scripts/verify-vercel-runtime.mjs` (`pnpm verify:vercel-runtime`), which fails with a clear message if the two JSON files diverge semantically, if `support.ts` does not import the local runtime copy, or if it still imports from `../../../../examples/`. Wired into `build:vercel` and `verify`.
- Fixed a second, independently discovered defect in the same area: `pnpm smoke:preview -- <url>` and `pnpm smoke:vercel-local -- <url>` read `process.argv[3]` directly, which is the literal `--` token pnpm forwards, not the URL. Both tasks now skip a literal `--` when locating the trailing argument.

## Verification

- `pnpm verify:vercel-runtime`, `pnpm --filter @opstwin/web typecheck`, `pnpm --filter @opstwin/web lint`, and `pnpm --filter @opstwin/web build` all passed locally before any commit. The local `next build` completed fully (`✓ Compiled successfully`, `✓ Generating static pages (4/4)`) — the missing-module error was fixed, compilation passed, and there was no later environment blocker to distinguish.
- `pnpm verify` passed completely end to end for the first time in this project's history on this macOS host (Node 22.22.3, pnpm 11.7.0, Python 3.12.13): ruff, ESLint, mypy (51 files), `tsc --noEmit`, the full backend pytest suite (247/247, including a new observer-failure regression test), the full Vitest suite (18/18 files, 140/140 tests — previously environment-blocked in every prior sprint), both production builds, the canonical CLI example, all six benchmark smokes with passing integrity, and deterministic source packaging/verification.
- `git diff --check` passed; an unrelated `apps/web/next-env.d.ts` diff produced by running `next build` locally was reverted before each commit to keep changes bounded.

## Deployment evidence

Full detail (routes, timings, response sizes, browser evidence) is recorded in `docs/VERCEL_PREVIEW_EVIDENCE.md`. Summary: the hotfix was pushed as `72607de`, and the Git-integrated Vercel build for `ops-twin` started within seconds and completed as `Ready` (production, region `iad1`) with no missing-module error — `next build` and the FastAPI (`python3.12`) function packaging both completed cleanly. `/`, `/workspace`, `/api/simulation/health`, and all six analysis routes returned correct evidence at bounded run counts (10, 25, and the existing 50-run canonical fixture), each with `integrity.status: "passed"`. The over-budget request (500 runs × 1,000 items) was correctly rejected with `WORK_BUDGET_EXCEEDED` rather than raising the limit. `pnpm smoke:preview -- https://ops-twin.vercel.app` passed in full. Two further commits (`2feb636`, the smoke-script argument fix; `1c571ec`, the economics observer fix below) each triggered and passed their own Vercel builds.

## Browser evidence

The in-app browser completed the full product journey against the deployed app: landing → `/workspace` → baseline assumptions → the two default scenarios → a 50-run paired comparison → every analysis tab (Overview, Metrics, Risk, Resources, Technical evidence) → Flow → Sensitivity → Economics → Playback (source toggle, restart/step/seek/speed/important-event navigation, a 542-row captioned event ledger, item journey inspector) → JSON and CSV exports. Console and network logs stayed empty of errors throughout; no request failed; no `localhost`/`127.0.0.1` reference was found in the rendered document. At 390×844, 768×1024, and 1440×900, the page itself never scrolled horizontally — wide content (the metrics table, the event ledger, the analysis tab strip) contains its own width inside an `overflow-x: auto` wrapper. Zero elements with a positive `tabindex` and zero unlabeled buttons or inputs were found sitewide; a `role="alert"` message and a `aria-live="polite"` region were both confirmed present and correctly triggered.

## Defects found

1. The Vercel packaging defect described above (fixed).
2. `pnpm smoke:preview`/`smoke:vercel-local`'s `--`-argument handling (fixed).
3. The economic-sensitivity observer used a bare `except Exception: <increment a counter>`, silently discarding any unexpected evaluation failure with no structured evidence, unlike the paired comparison observer hardened in Sprint 09.1 (fixed — see below).
4. One suspected UX defect (the economics panel appearing not to show a validation message for a negative cost rate) was investigated and found to be a false alarm: the message exists (`role="alert"`, `"Configured costs must be finite and at least zero."`); an earlier DOM-slice check simply missed it. No code change was needed.

## Defects fixed

The economic-sensitivity observer (`apps/simulation-api/app/economics/sensitivity.py`) now mirrors the comparison observer's pattern exactly: it logs the exception type (never the raw message) via `logging.warning`, classifies the error into a safe fixed message (`"economic evaluation raised a validation error"` for `ValueError | KeyError | TypeError | ZeroDivisionError`, otherwise `"...an unexpected error"`), and appends a new `EconomicSensitivityObserverFailure` (`testedValue`, `runIndex`, `errorCategory`, `message`) to a new additive `EconomicSensitivityExecutionMetadata.observerFailures` field (contract `0.7.0`, default empty list). Operational sensitivity results are unaffected — an observer failure only removes that tested value's run from economic pairing, exactly as before. `contracts/economic-sensitivity-result.schema.json` was updated to match, generated directly from the Pydantic model's `model_json_schema(by_alias=True)` output to guarantee an exact match, and validated by the existing `test_economic_delivery.py` schema-parity test. A focused regression test (`test_sensitivity_observer_failure_is_isolated_and_recorded`) injects a synthetic failure on a non-baseline tested value and asserts the operational sensitivity stays valid, exactly one categorized failure is recorded, and the message contains no path, exception-detail, or traceback leakage.

## Remaining limitations

- **GM-136 (reduced-motion behavior)** remains partial: the `reducedMotion` gate on the playback timer effect is unchanged and source-reviewed, and `matchMedia('(prefers-reduced-motion: reduce)').matches` was confirmed `false` (the default) in the browser QA session, but no automated `matchMedia`-mocked test or manual reduced-motion-preference browser run was executed this sprint.
- **GM-138 (playback payload boundary)** is unchanged this sprint; still recorded only in `docs/PLAYBACK_PERFORMANCE.md` from Sprint 10.
- Single-request timings recorded in `docs/VERCEL_PREVIEW_EVIDENCE.md` are one deployment's measurements at one point in time, not a load test or a hosting-capacity claim.
- The Results/Analysis panel (Overview/Metrics/Risk/Resources/Technical, exports) is the last section on the `/workspace` page, after Flow, Sensitivity, Economics, and the full Playback panel — a pre-existing layout from earlier sprints, not introduced this sprint. Focus is moved there programmatically after a comparison completes (confirmed via `document.activeElement`), so keyboard/assistive-technology users reach it immediately; sighted mouse users must scroll past the other sections. This was observed but not changed, because reordering top-level page sections is an architecture-level layout decision outside this sprint's "polish only demonstrated defects, do not redesign the whole product" scope.

## Acceptance criteria

All met: the web runtime template no longer imports from ignored `examples/`; `pnpm verify:vercel-runtime` passes; a new commit was pushed and Vercel built it; both services deployed in one project behind one domain; `/`, `/workspace`, and `/api/simulation/health` work; small simulation, comparison, sensitivity, and economics requests work; `pnpm smoke:preview` passed; the full browser product journey, playback, and exports were verified; all three required viewports were checked with no page-level horizontal scroll; accessibility-critical interactions were checked with zero violations found; no console or hydration errors were observed; the economic-sensitivity observer now records safe structured evidence; ADR-014 is accepted with evidence; documentation reflects the actual deployed state; no new major analytical capability was added.

## Rollback plan

If the hotfix regresses: revert commit `72607de` only, temporarily restore the `../../../../examples/` import, and (only as an emergency fallback) remove `examples/` from `.vercelignore`, then redeploy and record the temporary architecture debt. If a deployed runtime defect appears: identify the last known good deployment, roll back in Vercel, reproduce locally, apply a minimal source fix, and redeploy from a new commit. No analytical formula was or should be modified as a deployment workaround.
