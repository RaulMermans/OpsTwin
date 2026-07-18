"use client";

import { useEffect, useMemo, useReducer, useRef, useState } from "react";

import type { ComparisonResult } from "../../lib/api/simulation";
import { buildPlaybackExport } from "../../lib/playback/export";
import { deriveImportantEvents, nextImportantEventIndex, previousImportantEventIndex } from "../../lib/playback/important-events";
import { buildItemJourney } from "../../lib/playback/journey";
import { extractRepresentativeSource, normalizeEvents } from "../../lib/playback/normalize";
import { downloadText } from "../../lib/scenario-lab/exports";
import { asRecord, asRecords } from "../../lib/scenario-lab/result-adapter";
import { initialPlaybackState, intervalMsForSpeed, playbackReducer, type PlaybackAction, type PlaybackSpeed, type PlaybackState } from "../../lib/playback/controller";
import { buildTimeline, frameAtCheckpointIndex } from "../../lib/playback/timeline";
import type { WorkflowOperationalModel } from "../../lib/workflow/presentation-model";

const DISCLAIMER = "This playback illustrates one representative sampled run. Aggregate metrics, probabilities, and confidence intervals are calculated across all successful runs.";
const SPEEDS: PlaybackSpeed[] = [0.5, 1, 2, 4];

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;
}

export function PlaybackPanel({ result, model }: { result: ComparisonResult | null; model: WorkflowOperationalModel | null }) {
  const [mode, setMode] = useState<"baseline" | "scenario">("baseline");
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [ledgerFilter, setLedgerFilter] = useState<{ itemId: string | null; stageId: string | null; resourcePoolId: string | null; category: string | null }>({ itemId: null, stageId: null, resourcePoolId: null, category: null });
  const [resetKey, setResetKey] = useState<string | null>(null);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const representatives = asRecord(result?.representatives);
  const baselineVariant = representatives?.baseline ?? null;
  const scenarioVariant = representatives?.scenario ?? null;
  const scenarioEntry = scenarioVariant ? asRecords(result?.scenarios).find((item) => item.scenarioId === asRecord(scenarioVariant)?.variantId) : null;

  const baselineSource = useMemo(
    () => extractRepresentativeSource("baseline", baselineVariant, null, result?.baselineModelHash ?? null),
    [baselineVariant, result?.baselineModelHash],
  );
  const scenarioSource = useMemo(
    () => extractRepresentativeSource("scenario", scenarioVariant, scenarioEntry ? String(scenarioEntry.scenarioName ?? scenarioEntry.scenarioId) : null, scenarioEntry ? String(scenarioEntry.scenarioModelHash ?? "") || null : null),
    [scenarioVariant, scenarioEntry],
  );

  const activeSource = mode === "scenario" && scenarioSource ? scenarioSource : baselineSource;

  const { events: normalizedEvents, warnings } = useMemo(
    () => activeSource ? normalizeEvents(activeSource.events) : { events: [], warnings: [] },
    [activeSource],
  );
  const timeline = useMemo(() => buildTimeline(normalizedEvents, warnings), [normalizedEvents, warnings]);
  const resourceCapacities = useMemo(() => Object.fromEntries((model?.resourcePools ?? []).map((pool) => [pool.id, pool.capacity ?? 0])), [model]);
  const importantEvents = useMemo(() => deriveImportantEvents(timeline, resourceCapacities), [timeline, resourceCapacities]);
  const slaTargetDuration = model?.slaRules?.[0]?.targetDuration ?? null;

  const [state, dispatch] = useReducer(
    (playbackState: PlaybackState, action: PlaybackAction) => playbackReducer(playbackState, action, timeline.checkpoints.length),
    undefined,
    initialPlaybackState,
  );

  // Reset playback and the selected item whenever the representative source
  // changes. This adjusts state during render (React's documented escape
  // hatch for "resetting state without an Effect") rather than doing it in
  // an Effect, which avoids a cascading-render synchronous setState call.
  const sourceKey = activeSource
    ? `${activeSource.selection.variant}:${activeSource.selection.variantId}:${activeSource.selection.runIndex}:${activeSource.selection.seed}`
    : null;
  if (sourceKey !== resetKey) {
    setResetKey(sourceKey);
    setSelectedItemId(null);
    dispatch({ type: "restart" });
  }

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (state.playing && !reducedMotion) {
      timerRef.current = setInterval(() => dispatch({ type: "tick" }), intervalMsForSpeed(state.speed));
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [state.playing, state.speed, reducedMotion]);

  const frame = frameAtCheckpointIndex(timeline, state.checkpointIndex);
  const currentTime = frame.simulationTime;
  const announcement = state.playing
    ? "Playback started."
    : state.checkpointIndex >= timeline.checkpoints.length - 1 && timeline.checkpoints.length > 0
      ? "Playback completed."
      : "";

  if (!activeSource) {
    return <section className="playback-section" aria-labelledby="playback-title">
      <h2 id="playback-title">Representative playback</h2>
      <p className="empty-state">Representative playback is unavailable while aggregate analysis remains valid. No representative sampled run was retained for the current selection.</p>
    </section>;
  }

  const selection = activeSource.selection;
  const bothPaired = mode === "scenario" && baselineSource && scenarioSource && baselineSource.selection.runIndex === scenarioSource.selection.runIndex && baselineSource.selection.seed === scenarioSource.selection.seed;

  const filteredEvents = timeline.events.filter((event) =>
    (!ledgerFilter.itemId || event.itemId === ledgerFilter.itemId) &&
    (!ledgerFilter.stageId || event.stageId === ledgerFilter.stageId) &&
    (!ledgerFilter.resourcePoolId || event.resourcePoolId === ledgerFilter.resourcePoolId) &&
    (!ledgerFilter.category || event.eventType === ledgerFilter.category),
  );
  const filterActive = Boolean(ledgerFilter.itemId || ledgerFilter.stageId || ledgerFilter.resourcePoolId || ledgerFilter.category);

  const journey = selectedItemId ? buildItemJourney(timeline, selectedItemId, slaTargetDuration) : null;

  const temporalSummary = buildTemporalSummary(timeline, importantEvents);

  function seekToTime(time: number) {
    const nearestIndex = timeline.checkpoints.findIndex((checkpoint) => checkpoint.simulationTime >= time);
    dispatch({ type: "seek", checkpointIndex: nearestIndex === -1 ? timeline.checkpoints.length - 1 : nearestIndex });
  }

  function exportJson() {
    const payload = buildPlaybackExport(selection, timeline.events, temporalSummary, selectedItemId ? [buildItemJourney(timeline, selectedItemId, slaTargetDuration)] : [], timeline.warnings);
    downloadText("opstwin-playback-presentation.json", JSON.stringify(payload, null, 2), "application/json");
  }

  return <section className="playback-section" aria-labelledby="playback-title">
    <div className="playback-heading">
      <div>
        <p className="section-eyebrow">Representative sampled-run evidence</p>
        <h2 id="playback-title">Representative playback</h2>
        <p className="playback-disclaimer">{DISCLAIMER}</p>
      </div>
      <button className="secondary" type="button" onClick={exportJson}>Export playback JSON</button>
    </div>

    <div className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</div>

    <div className="playback-mode-toggle" role="group" aria-label="Representative source">
      <button type="button" aria-pressed={mode === "baseline"} onClick={() => setMode("baseline")}>Baseline representative</button>
      <button type="button" aria-pressed={mode === "scenario"} disabled={!scenarioSource} onClick={() => setMode("scenario")}>Selected scenario representative{!scenarioSource ? " (unavailable)" : ""}</button>
    </div>
    <p className="playback-identity">
      Run index {selection.runIndex} · seed {selection.seed} · selection method {selection.selectionMethod}
      {selection.modelHash && <> · model hash <code>{selection.modelHash.slice(0, 12)}</code></>}
    </p>
    {mode === "scenario" && scenarioSource && baselineSource && (
      <p className="playback-identity">{bothPaired ? "Both playbacks use the same paired run index and seed." : "These are separately selected representative runs and should not be interpreted as event-level paired equivalents."}</p>
    )}

    <div className="playback-controls" role="group" aria-label="Playback controls">
      <button type="button" onClick={() => dispatch({ type: "restart" })} aria-label="Restart playback">Restart</button>
      <button type="button" onClick={() => dispatch({ type: "stepBackward" })} aria-label="Step backward one event group">Step back</button>
      <button type="button" onClick={() => dispatch(state.playing ? { type: "pause" } : { type: "play" })} aria-label={state.playing ? "Pause playback" : "Play playback"}>{state.playing ? "Pause" : "Play"}</button>
      <button type="button" onClick={() => dispatch({ type: "stepForward" })} aria-label="Step forward one event group">Step forward</button>
      <label className="playback-speed">Speed<select aria-label="Playback speed" value={state.speed} onChange={(event) => dispatch({ type: "setSpeed", speed: Number(event.target.value) as PlaybackSpeed })}>{SPEEDS.map((speed) => <option key={speed} value={speed}>{speed}×</option>)}</select></label>
      <button type="button" onClick={() => { const next = nextImportantEventIndex(importantEvents, frame.eventIndex); if (next !== null) { const target = timeline.checkpoints.findIndex((c) => c.eventIndex === next || c.eventIndex >= next); dispatch({ type: "seek", checkpointIndex: target === -1 ? timeline.checkpoints.length - 1 : target }); } }}>Next important event</button>
      <button type="button" onClick={() => { const prev = previousImportantEventIndex(importantEvents, frame.eventIndex); if (prev !== null) { const target = timeline.checkpoints.findIndex((c) => c.eventIndex >= prev); dispatch({ type: "seek", checkpointIndex: target === -1 ? 0 : target }); } }}>Previous important event</button>
    </div>
    <label className="playback-slider">
      Simulation time
      <input type="range" aria-valuetext={`Simulation time ${currentTime}`} min={timeline.minTime} max={timeline.maxTime || timeline.minTime} step="any" value={currentTime} onChange={(event) => seekToTime(Number(event.target.value))} />
      <span>{currentTime} of {timeline.maxTime} (min {timeline.minTime})</span>
    </label>
    {reducedMotion && <p className="playback-hint">Reduced motion is enabled: playback defaults to paused, step-based interaction.</p>}

    <div className="playback-summary">
      <h3>Run-level temporal summary</h3>
      <ul>{temporalSummary.map((line, index) => <li key={index}>{line}</li>)}</ul>
    </div>

    <div className="playback-frame-text" aria-label="Current stage and resource state">
      <h3>Stage and resource state at time {currentTime}</h3>
      <table><caption>Waiting and processing counts by stage, and busy/capacity by resource pool.</caption>
        <thead><tr><th scope="col">Stage</th><th scope="col">Waiting</th><th scope="col">Processing</th></tr></thead>
        <tbody>{frame.stages.map((stage) => <tr key={stage.stageId}><th scope="row">{stage.stageId}</th><td>{stage.waitingItemIds.length}</td><td>{stage.processingItemIds.length}</td></tr>)}</tbody>
      </table>
      <table><caption>Resource pool busy count against configured capacity.</caption>
        <thead><tr><th scope="col">Resource pool</th><th scope="col">Busy</th><th scope="col">Capacity</th></tr></thead>
        <tbody>{frame.resources.map((resource) => <tr key={resource.resourcePoolId}><th scope="row">{resource.resourcePoolId}</th><td>{resource.busyItemIds.length}</td><td>{resourceCapacities[resource.resourcePoolId] ?? "Not available"}</td></tr>)}</tbody>
      </table>
      <p>Completed: {frame.completedItemIds.length} · Failed: {frame.failedItemIds.length} · In rework: {frame.reworkingItemIds.length}</p>
      {frame.integrityWarnings.length > 0 && <p className="inline-error" role="alert">{frame.integrityWarnings.join(" ")}</p>}
    </div>

    <EventLedger events={filteredEvents} currentEventIndex={frame.eventIndex} onSeekToEvent={(event) => seekToTime(event.simulationTime)} filter={ledgerFilter} setFilter={setLedgerFilter} filterActive={filterActive} allStageIds={[...new Set(timeline.events.map((e) => e.stageId).filter((v): v is string => v !== null))]} allResourceIds={[...new Set(timeline.events.map((e) => e.resourcePoolId).filter((v): v is string => v !== null))]} allItemIds={selection.selectedItemIds} />

    <ItemJourneyView selectedItemId={selectedItemId} setSelectedItemId={setSelectedItemId} selectedItemIds={selection.selectedItemIds} journey={journey} />
  </section>;
}

function buildTemporalSummary(timeline: ReturnType<typeof buildTimeline>, importantEvents: ReturnType<typeof deriveImportantEvents>): string[] {
  const lines: string[] = [];
  const maxQueue = [...importantEvents].reverse().find((item) => item.category === "maximum_sampled_queue_reached");
  if (maxQueue) lines.push(maxQueue.summary);
  for (const item of importantEvents.filter((event) => event.category === "resource_fully_utilized")) lines.push(item.summary);
  const reworkCount = importantEvents.filter((item) => item.category === "rework_started").length;
  if (reworkCount > 0) lines.push(`${reworkCount} sampled item${reworkCount === 1 ? "" : "s"} entered rework.`);
  const completions = importantEvents.filter((item) => item.category === "item_completed");
  if (completions.length > 0) lines.push(`The final sampled completion occurred at time ${completions[completions.length - 1].simulationTime}.`);
  const failures = importantEvents.filter((item) => item.category === "item_failed");
  if (failures.length > 0) lines.push(`${failures.length} sampled item${failures.length === 1 ? "" : "s"} reached terminal failure.`);
  if (lines.length === 0) lines.push("No run-level temporal events were derived from the retained sampled evidence.");
  return lines.map((line) => `Run-level: ${line}`);
}

function EventLedger({ events, currentEventIndex, onSeekToEvent, filter, setFilter, filterActive, allStageIds, allResourceIds, allItemIds }: {
  events: ReturnType<typeof buildTimeline>["events"];
  currentEventIndex: number;
  onSeekToEvent: (event: ReturnType<typeof buildTimeline>["events"][number]) => void;
  filter: { itemId: string | null; stageId: string | null; resourcePoolId: string | null; category: string | null };
  setFilter: (filter: { itemId: string | null; stageId: string | null; resourcePoolId: string | null; category: string | null }) => void;
  filterActive: boolean;
  allStageIds: string[];
  allResourceIds: string[];
  allItemIds: string[];
}) {
  return <div className="playback-ledger">
    <h3>Event ledger</h3>
    <div className="playback-ledger-filters">
      <label>Item<select aria-label="Filter by item" value={filter.itemId ?? ""} onChange={(event) => setFilter({ ...filter, itemId: event.target.value || null })}><option value="">All items</option>{allItemIds.map((id) => <option key={id} value={id}>{id}</option>)}</select></label>
      <label>Stage<select aria-label="Filter by stage" value={filter.stageId ?? ""} onChange={(event) => setFilter({ ...filter, stageId: event.target.value || null })}><option value="">All stages</option>{allStageIds.map((id) => <option key={id} value={id}>{id}</option>)}</select></label>
      <label>Resource<select aria-label="Filter by resource" value={filter.resourcePoolId ?? ""} onChange={(event) => setFilter({ ...filter, resourcePoolId: event.target.value || null })}><option value="">All resources</option>{allResourceIds.map((id) => <option key={id} value={id}>{id}</option>)}</select></label>
      {filterActive && <button type="button" className="text-button" onClick={() => setFilter({ itemId: null, stageId: null, resourcePoolId: null, category: null })}>Clear filters</button>}
    </div>
    <div className="metric-matrix-wrap">
      <table className="metric-matrix">
        <caption>Ordered representative event ledger. Selecting a row seeks playback to that event&apos;s time.</caption>
        <thead><tr><th scope="col">Time</th><th scope="col">Item</th><th scope="col">Event</th><th scope="col">Stage</th><th scope="col">Resource</th><th scope="col">Details</th></tr></thead>
        <tbody>{events.map((event) => <tr key={event.id} aria-current={event.index === currentEventIndex ? "true" : undefined} className={event.index === currentEventIndex ? "playback-current-row" : undefined} tabIndex={0} onClick={() => onSeekToEvent(event)} onKeyDown={(keyEvent) => { if (keyEvent.key === "Enter" || keyEvent.key === " ") { keyEvent.preventDefault(); onSeekToEvent(event); } }}>
          <td>{event.simulationTime}</td><td>{event.itemId ?? "Not available"}</td><td>{event.eventType}</td><td>{event.stageId ?? "Not available"}</td><td>{event.resourcePoolId ?? "Not available"}</td><td>{event.summary}</td>
        </tr>)}</tbody>
      </table>
    </div>
  </div>;
}

function ItemJourneyView({ selectedItemId, setSelectedItemId, selectedItemIds, journey }: { selectedItemId: string | null; setSelectedItemId: (id: string | null) => void; selectedItemIds: string[]; journey: ReturnType<typeof buildItemJourney> | null }) {
  return <div className="playback-journey">
    <h3>Item journey inspector</h3>
    <label>Sampled item<select aria-label="Select a sampled item" value={selectedItemId ?? ""} onChange={(event) => setSelectedItemId(event.target.value || null)}><option value="">Select an item</option>{selectedItemIds.map((id) => <option key={id} value={id}>{id}</option>)}</select></label>
    {journey && <dl className="technical-summary">
      <div><dt>Arrival time</dt><dd>{journey.arrivalTime ?? "Not available"}</dd></div>
      <div><dt>Total cycle time</dt><dd>{journey.cycleTime ?? "Not available"}</dd></div>
      <div><dt>Terminal state</dt><dd>{journey.completedAt !== null ? "Completed" : journey.failedAt !== null ? "Failed" : "Not terminal in the retained window"}</dd></div>
      <div><dt>SLA result</dt><dd>{journey.slaResult === "not_available" ? "Not available" : journey.slaResult}</dd></div>
      <div><dt>Rework loops</dt><dd>{journey.reworkCount}</dd></div>
    </dl>}
    {journey && <ol className="playback-visits">{journey.visits.map((visit) => <li key={visit.visitNumber}>Visit {visit.visitNumber}: {visit.stageId}{visit.reworked ? " (led to rework)" : ""} · wait {visit.waitingDuration ?? "Not available"} · processing {visit.processingDuration ?? "Not available"}</li>)}</ol>}
  </div>;
}
