# Sprint 10 — Representative-Run Playback and Temporal Explanation

## Objective

Add deterministic client-side playback of one retained representative sampled run so the product can explain when queues formed, how resources were used, where rework occurred, and how a scenario's representative differed from its baseline representative — without ever presenting one run as aggregate certainty.

## Current representative evidence

Contracts `0.4.0` (`RepeatedSimulationResult.representativeRun`) and `0.5.0` (`ScenarioComparisonResult.representatives`) already retain one `RepresentativeRunResult` per variant, selected by normalized-median-vector distance (ADR-010) and executed with the same paired seed schedule as its variant (ADR-012). Each carries `runIndex`, `seed`, `selectionMethod`, `detailMode`, `includedEventCount`, and a full `SimulationResult` with `observation`, `resultDetail.selectedItemIds`, and an ordered `events` array using the existing `EventType` vocabulary. See `docs/REPRESENTATIVE_PLAYBACK_SPEC.md` for the exact field audit and event-semantics mapping.

## In scope

Client-side event normalization; deterministic timeline/frame reconstruction with checkpointed seeking; a playback controller (play/pause/restart/step/seek/speed/important-event navigation); workflow-map overlay integration reusing the Sprint 07 presentation adapter; an accessible event ledger; an item journey inspector; baseline/scenario representative switching with correct paired-vs-separate identity disclosure; reduced-motion and keyboard accessibility; local JSON export; GM-122 through GM-140; `pnpm benchmark:playback`.

## Out of scope

Live simulation streaming, WebSockets, background simulation, full-event browser mode, video/GIF export, 3D visualization, particle systems, large animation libraries, aggregate-animation claims, root-cause claims, recommendations, workflow topology editing, persistence, authentication, cloud sharing, deployment.

## Playback limitations

Playback shows exactly one retained representative run per variant (never all runs). The retained event set is bounded by `sampledItemLimit` (default 25 items); items outside that sample are not visible. There is no distinct backend "queue exited," "resource acquired," or "SLA evaluated" event — those are documented derived frame semantics, not invented backend events (see spec). Baseline and scenario representatives are independently selected and are not guaranteed to share a run index/seed; the UI discloses which case applies rather than assuming pairing.

## Aggregate-versus-run distinction

Every playback view carries the fixed disclaimer text from ADR-021 and a separate, always-visible "Aggregate evidence across successful runs" panel. Aggregate confidence intervals and probabilities are never rendered on the playback timeline itself.

## Architecture

Pure TypeScript modules under `apps/web/lib/playback/`: `types.ts` (presentation types), `normalize.ts` (representative result → `PlaybackEvent[]`), `timeline.ts` (`PlaybackEvent[]` → `PlaybackTimeline` with checkpoints, `buildFrame(timeline, time)` → `PlaybackFrame`), `controller.ts` (framework-agnostic playback state machine), `important-events.ts`, `journey.ts` (item journey derivation), `export.ts`. `apps/web/components/playback/` hosts the React presentation: `playback-panel.tsx`, `event-ledger.tsx`, `item-journey.tsx`, wired into the existing `WorkflowVisualization` for overlay counts. No backend change; ADR-022 documents why reconstruction is entirely client-side.

## Accessibility

Reduced-motion default-paused behavior, a polite live region for state changes, a fully labelled range slider, keyboard-operable controls and ledger rows, and a complete non-visual equivalent (ledger + item journey) for every visual state. See spec "Accessibility"/"Reduced motion."

## Performance limits

No simulation rerun, no network request, checkpointed reconstruction instead of full replay per tick, one controlled interval timer, bounded DOM output during the `pnpm benchmark:playback` fixtures (10/100, 25/500, 25/1000, 50/2000 items/events).

## Tests

Pure-function unit tests for normalization, timeline reconstruction, controller determinism, ledger/journey derivation, and the restricted-language scan, per CLAUDE.md section 43 and golden models GM-122–GM-140.

## Acceptance criteria

AC5–AC10 in `CLAUDE.md` (representative source, timeline reconstruction, controls, workflow/ledger, evidence boundaries, performance/payload).

## Definition of done

Pure playback modules and their tests are source-green under direct `vitest`/`tsc` execution; the playback panel is wired into the workspace behind existing representative evidence with no new backend request; `pnpm benchmark:playback` runs against local fixtures; docs and `SCRATCHPAD.md` are updated; no Git or deployment action occurs.

## Rollback plan

If playback destabilizes the Scenario Lab, remove only the `PlaybackPanel` mount point from the workspace composition (one JSX line) while keeping the isolated pure modules and their tests intact; the existing workflow visualization, ledger-free Scenario Lab, and aggregate evidence panels are unaffected because playback never alters comparison requests or results. No simulation event semantics are changed by this rollback.
