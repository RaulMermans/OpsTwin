---
name: verify-representative-playback
description: Verify OpsTwin Sprint 10 representative-run playback — normalization, timeline reconstruction, controller determinism, ledger/journey, aggregate/playback disclaimer, accessibility, payload bounds, export safety, and restricted language.
---

# Verify representative playback

1. Read `docs/REPRESENTATIVE_PLAYBACK_SPEC.md`, `docs/sprints/SPRINT_10_REPRESENTATIVE_PLAYBACK.md`, ADR-021, ADR-022, and GM-122 through GM-140 in `docs/VALIDATION_PLAN.md`.
2. Inspect only `apps/web/lib/playback/*`, `apps/web/components/playback/*`, their tests under `apps/web/tests/playback-*`, and their integration point in `apps/web/app/workspace/workspace.tsx`.
3. Verify representative metadata: run index, seed, selection method, model hash, and observation window are read from the existing `0.4.0`/`0.5.0` representative fields with no new backend contract.
4. Verify event ordering (`simulationTime` then original index), duplicate-ID rejection, non-finite-time rejection, and safe handling of unknown event types.
5. Verify timeline reconstruction: queue/processing/resource occupancy, rework as a distinct visit, completion/failure terminal state, no negative counts, and deterministic `buildFrame` (seeking to the same time twice returns an equal frame).
6. Verify the playback controller: play/pause/restart/step/seek/speed, one timer only, auto-pause at the end, and that a scenario/baseline switch resets to the initial frame.
7. Verify the event ledger (caption, headers, current-row identification, row-seek, filters, keyboard activation) and the item journey (visits, rework loops, SLA result, terminal evidence) are built only from retained sampled evidence.
8. Verify the fixed representative-playback disclaimer and the separate "Aggregate evidence across successful runs" label are both present, and that no aggregate confidence value is rendered on the playback timeline.
9. Verify accessibility: labelled controls, a slider with min/max/step/value, a polite live region, and `prefers-reduced-motion` defaulting to paused/step-based interaction without hiding any information.
10. Run `node scripts/benchmark-playback.mjs` and confirm `docs/PLAYBACK_PERFORMANCE.md` is written with no simulation rerun and no network request.
11. Scan rendered playback copy for restricted language (`typical run`, `proves`, `root cause`, `recommended`, `best action`, `optimal`, `winning scenario`, `you should`, `guaranteed`), case-insensitive.
12. Run available targeted checks (`tsc --noEmit`, `eslint`, direct `vitest run` on the `playback-*` test files) via local binaries. Report exact executed/blocked status; a sandbox-blocked worker/child-process pool must be reported as blocked, never as passed.
