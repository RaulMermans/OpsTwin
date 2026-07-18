# Representative Playback Specification

## Purpose

Explain temporal behavior of one retained representative sampled run — when queues formed, how resources were used, where rework occurred, how the run reached completion or failure — without presenting that one run as aggregate certainty.

## User

The same operations/business user as the Scenario Lab (`SCENARIO_LAB_SPEC.md`), now asking "what actually happened during a representative run" after already seeing aggregate comparison evidence.

## Representative-selection evidence

Playback consumes `RepresentativeRunResult` exactly as returned by contracts `0.4.0` (`RepeatedSimulationResult.representativeRun`) and `0.5.0` (`ScenarioComparisonResult.representatives.baseline` / `.scenario`, each a `RepresentativeVariantResult { variantId, representative }`). Required fields, all already present and none invented for this sprint: `runIndex`, `seed`, `selectionMethod` (`"normalized_median_vector"`), `distance`, `medianVector`, `metricVector`, `rerunSnapshotMatches`, `detailMode`, `includedEventCount`, and `result` (a full `SimulationResult` carrying `observation`, `resultDetail.selectedItemIds`, and `events`). Model hash is read from `ScenarioComparisonResult.baselineModelHash` / the matching `ScenarioComparisonEntry.scenarioModelHash`.

## Inputs

Playback never issues a new simulation request. It is a pure presentation layer over a comparison or repeated result the workspace already fetched with `representativeEvidence.detailMode = "sampled"` (default `sampledItemLimit: 25`). If the caller only requested `summary` detail, no representative events exist and playback reports the "representative source unavailable" empty state rather than requesting `full` detail as a workaround.

## Event semantics

Normalized events reuse the existing backend `EventType` vocabulary without inventing new event kinds:

| Backend `EventType` | Playback meaning |
| --- | --- |
| `ITEM_CREATED` | Item arrival |
| `QUEUE_ENTERED` | Item enters a stage's actual wait queue |
| `RESOURCE_REQUESTED` | Item requests a unit of a resource pool |
| `PROCESS_STARTED` | Processing begins (implies the queue wait for this visit ended and the resource was acquired at this same simulation time) |
| `PROCESS_COMPLETED` | Processing ends for this stage visit |
| `RESOURCE_RELEASED` | The resource unit becomes free again |
| `ROUTE_SELECTED` | A route option was chosen after this stage |
| `ITEM_REWORKED` | The item returned to an earlier stage via a failure/rework route |
| `ITEM_FAILED` | The item reached terminal failure |
| `ITEM_COMPLETED` | The item reached terminal completion |

There is no distinct backend "queue exited" or "resource acquired" event; the frame reconstructor derives those transitions from the adjacent `PROCESS_STARTED` event at the same `(itemId, stageId)` pair rather than inventing a new event type. There is no `SLA_EVALUATED` event; SLA attainment for a completed/failed item is a *derived* fact computed client-side from the already-available operational model's `slaRules[].targetDuration` and the item's cycle time (completion/failure time minus arrival time), using the exact formula in `METRIC_DEFINITIONS.md` ("successful included items at or below the applicable target"). This derivation is documented, not hidden, and is labelled "derived from the retained representative event log" wherever shown.

## Timeline semantics

Normalized events are sorted by `(simulationTime, sequence)` — `sequence` is the original backend event index, already monotonic per run, and is the documented tiebreak for equal `simulationTime` (GM-123). A normalized event carries a stable ID (`${itemId}:${sequence}`), the numeric event index in the sorted array, and a human-readable factual summary built from the same fields already on `SimulationEvent` (no invented text beyond formatting).

## Frame reconstruction

A pure function `buildFrame(timeline, atTime)` returns, for the requested simulation time: current time and event index, the events occurring exactly at that time, items waiting per stage (derived from unmatched `QUEUE_ENTERED` without a later `PROCESS_STARTED` at or before `atTime`), items processing per stage (`PROCESS_STARTED` without a later `PROCESS_COMPLETED`/`ITEM_FAILED` at or before `atTime`), resources busy per pool (unmatched `RESOURCE_REQUESTED`→`RESOURCE_RELEASED` pairs), resource capacity (read from the operational model, not derived), completed/failed/reworked sampled items so far, the selected item's state, and integrity warnings for anything the reconstructor could not resolve (e.g. a `PROCESS_COMPLETED` with no matching `PROCESS_STARTED` — reported as a warning, never silently corrected).

Reconstruction is fully re-derivable from index 0 for correctness, but the implementation precomputes periodic checkpoints (see Performance) so that interactive seeking does not replay the whole event array on every tick.

## Stage state

Waiting and processing counts per stage are non-negative integers; a stage with no visible sampled items at a given time reports `0`, never `null`. Only actually-waiting items count toward "waiting" (matches `METRIC_DEFINITIONS.md`: immediate grants never add queue area).

## Queue state

Maximum observed sampled queue and its time are tracked incrementally while building checkpoints and exposed as one of the "important events" (Maximum observed sampled queue reached).

## Resource state

Busy count per pool never exceeds the pool's configured capacity from the operational model unless the source event evidence itself reports an integrity anomaly, in which case a warning is attached rather than clamping the number silently.

## Item state

Each sampled item's state is one of `arrived`, `waiting`, `processing`, `in_rework`, `completed`, `failed`, derived from its own event subsequence. Repeated stage visits (rework loops) remain distinct entries in the item's visit list — they are never collapsed into one row.

## Completion

`ITEM_COMPLETED` sets the item terminal state to `completed` and contributes to the running completed-sampled-items count and the "final sampled completion" temporal-summary fact.

## Failure

`ITEM_FAILED` sets the item terminal state to `failed` and contributes to the running failed-sampled-items count.

## Rework

`ITEM_REWORKED` marks a rework loop start; the item's next `QUEUE_ENTERED` at the target stage begins a new, distinctly numbered visit. The temporal summary counts sampled items that entered rework at least once.

## Controls

Play, pause, restart, step forward/backward by one event group (all normalized events sharing the same `simulationTime`), seek via a labelled range slider (min/max/step/current all exposed to assistive technology), jump to next/previous important event, and speed `0.5×/1×/2×/4×`. Exactly one interval timer drives automatic playback; it is cleared on unmount, on scenario/baseline source switch, and when playback reaches the end (auto-pause). A user-initiated seek pauses playback. Speed only changes the timer interval, never event ordering or reconstructed state.

## Event ledger

An accessible table (`Time`, `Item`, `Event`, `Stage`, `Resource`, `Details`) with a caption, proper `<th>` headers, one identified "current" row, row activation that seeks playback to that event's time, keyboard row selection (Enter/Space), and filters by item/stage/resource/event-category that only affect what is displayed, never the underlying normalized evidence. Unknown/missing fields render the literal text "Not available". A "Clear filters" action always exists when any filter is active.

## Item journey

Selecting one sampled item shows: item ID, arrival time, ordered stage visits (including distinct rework visits) with queue wait and processing duration per visit, resource pool per visit, route decisions taken, completion or failure time, total observed cycle time, the derived SLA result (see Event semantics), and the item's live state at the current playback time. Selecting an item filters the ledger to that item's events but never hides the stage-level aggregate counts shown elsewhere.

## Baseline/scenario switching

A toggle switches between the baseline representative and the selected scenario's representative (when the scenario is eligible and a representative was retained). Switching always pauses playback and resets to the initial frame (documented behavior: "Switching representative source resets playback to the beginning"); it never merges the two event streams. The current mode, run index, seed, selection method, and (in the technical-evidence disclosure) model hash are always explicit. If `representatives.baseline` or `representatives.scenario` is `null` (e.g. no scenario was eligible), the corresponding toggle option is disabled with a factual explanation, and aggregate evidence remains available regardless.

## Representative identity disclosure

If `representatives.baseline.representative.runIndex === representatives.scenario.representative.runIndex` and the seeds are also equal, the panel states: "Both playbacks use the same paired run index and seed." Otherwise it states: "These are separately selected representative runs and should not be interpreted as event-level paired equivalents." This is computed at render time from the two `RepresentativeRunResult` objects already returned; it is never inferred from aggregate pairing statistics.

## Accessibility

All controls have accessible names; documented keyboard shortcuts exist for play/pause, step, and seek; the timeline slider exposes current/min/max/step; a polite live region announces playback started/paused/current time (throttled)/important events/playback completed, without announcing every minor automatic-playback event. `prefers-reduced-motion` defaults playback to paused/step-based interaction, disables the route-highlight transition, and never hides information — the event ledger and item journey remain the complete non-visual equivalent of every visual state.

## Reduced motion

See Accessibility. Reduced-motion mode changes only animation/timer defaults, never available data.

## Responsive behavior

390×844: vertical workflow/list mode, compact control bar, full-width slider, stacked ledger rows, item journey below playback, no required horizontal scroll. 768×1024: workflow above inspector, ledger below, controls wrap without overflow. 1440×900: workflow and inspector may sit side by side with the ledger adjacent or below.

## Exports

Client-side `playback-presentation.json` containing export version, source type (baseline/scenario), scenario ID, run index, seed, selection method, observation window, normalized events, temporal summary, item journeys, and integrity warnings. Excludes full unretained event history (there is none beyond the retained sampled set), browser timer state, internal React state, filesystem paths, stack traces, and secrets. No video/GIF/image export.

## Failure modes

No representative evidence, empty event list, non-finite event time, duplicate event ID, unknown event type, unknown stage/resource reference, missing item ID, a scenario representative that failed to retain, an unavailable baseline representative, and a representative source that changes mid-playback are all handled without crashing the Scenario Lab: playback reports "Representative playback is unavailable; aggregate analysis remains valid" and aggregate evidence keeps rendering normally. No other run is silently substituted.

## Outputs

A `PlaybackTimeline` (normalized events, checkpoints, integrity warnings), a `PlaybackFrame` at the current time, the playback controller's state, the event ledger, the item journey view, and the JSON export — none of these are simulation inputs and none feed back into ranking, guardrails, or aggregate statistics.

## Deferred capabilities

Live simulation streaming, WebSockets, background simulation, full-event browser mode, video/GIF export, 3D visualization, particle systems, large animation libraries, aggregate-animation claims, root-cause claims, recommendations, workflow editing, persistence, authentication, cloud sharing, and deployment.
