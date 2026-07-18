// Local performance guard for representative-run playback reconstruction.
//
// This script measures the same two algorithms implemented in
// apps/web/lib/playback/normalize.ts and apps/web/lib/playback/timeline.ts.
// Node on this repo's supported runtimes cannot execute .ts sources
// directly, so the measured functions below are a mechanical (type-erased)
// transliteration of those two modules — not an independent
// reimplementation — kept intentionally minimal and structurally identical
// so the measured algorithmic cost matches the shipped TypeScript. No
// simulation reruns and no network requests occur here.

import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputPath = resolve(root, "docs", "PLAYBACK_PERFORMANCE.md");

const EVENT_TYPES = [
  "ITEM_CREATED", "QUEUE_ENTERED", "RESOURCE_REQUESTED", "PROCESS_STARTED",
  "PROCESS_COMPLETED", "RESOURCE_RELEASED", "ROUTE_SELECTED", "ITEM_FAILED",
  "ITEM_REWORKED", "ITEM_COMPLETED",
];

function normalizeEvents(rawEvents) {
  const warnings = [];
  const seenIds = new Set();
  const staged = [];
  rawEvents.forEach((event, sourceIndex) => {
    const simulationTime = event.simulationTime;
    if (typeof simulationTime !== "number" || !Number.isFinite(simulationTime)) {
      warnings.push({ code: "non_finite_time", detail: `index ${sourceIndex}` });
      return;
    }
    const eventType = EVENT_TYPES.includes(event.eventType) ? event.eventType : "UNKNOWN";
    const itemId = event.itemId ?? null;
    if (itemId === null) {
      warnings.push({ code: "missing_item_id", detail: `index ${sourceIndex}` });
      return;
    }
    const id = typeof event.sequence === "number" ? String(event.sequence) : `idx:${sourceIndex}`;
    if (seenIds.has(id)) {
      warnings.push({ code: "duplicate_event_id", detail: `index ${sourceIndex}` });
      return;
    }
    seenIds.add(id);
    staged.push({ id, simulationTime, eventType, itemId, stageId: event.stageId ?? null, resourcePoolId: event.resourcePoolId ?? null, sourceIndex });
  });
  staged.sort((a, b) => a.simulationTime - b.simulationTime || a.sourceIndex - b.sourceIndex);
  const events = staged.map((event, index) => ({ ...event, index }));
  return { events, warnings };
}

function buildTimeline(events) {
  const waiting = new Map();
  const processing = new Map();
  const busy = new Map();
  const completed = new Set();
  const failed = new Set();
  function addTo(map, key, itemId) { if (!key) return; if (!map.has(key)) map.set(key, new Set()); map.get(key).add(itemId); }
  function removeFrom(map, key, itemId) { if (!key) return; map.get(key)?.delete(itemId); }
  function removeEverywhere(itemId) { for (const set of waiting.values()) set.delete(itemId); for (const set of processing.values()) set.delete(itemId); for (const set of busy.values()) set.delete(itemId); }

  const checkpoints = [];
  let groupStart = 0;
  while (groupStart < events.length) {
    let groupEnd = groupStart;
    const time = events[groupStart].simulationTime;
    while (groupEnd < events.length && events[groupEnd].simulationTime === time) groupEnd++;
    for (let i = groupStart; i < groupEnd; i++) {
      const event = events[i];
      const itemId = event.itemId;
      switch (event.eventType) {
        case "QUEUE_ENTERED": addTo(waiting, event.stageId, itemId); break;
        case "PROCESS_STARTED": removeFrom(waiting, event.stageId, itemId); addTo(processing, event.stageId, itemId); addTo(busy, event.resourcePoolId, itemId); break;
        case "PROCESS_COMPLETED": removeFrom(processing, event.stageId, itemId); break;
        case "RESOURCE_RELEASED": removeFrom(busy, event.resourcePoolId, itemId); break;
        case "ITEM_FAILED": removeEverywhere(itemId); failed.add(itemId); break;
        case "ITEM_COMPLETED": removeEverywhere(itemId); completed.add(itemId); break;
        default: break;
      }
    }
    checkpoints.push({ eventIndex: groupEnd - 1, simulationTime: time, waitingCount: [...waiting.values()].reduce((s, set) => s + set.size, 0) });
    groupStart = groupEnd;
  }
  return { checkpoints, completedCount: completed.size, failedCount: failed.size };
}

function generateFixture(itemCount, eventCount) {
  const stages = ["triage", "level-1", "level-2", "quality-check"];
  const events = [];
  let sequence = 0;
  for (let i = 0; i < itemCount; i++) {
    const itemId = `item-${i}`;
    let time = i;
    events.push({ sequence: sequence++, simulationTime: time, eventType: "ITEM_CREATED", itemId });
    const visitsForItem = Math.max(1, Math.round(eventCount / itemCount / 4));
    for (let v = 0; v < visitsForItem; v++) {
      const stage = stages[v % stages.length];
      events.push({ sequence: sequence++, simulationTime: time, eventType: "QUEUE_ENTERED", itemId, stageId: stage });
      time += 1;
      events.push({ sequence: sequence++, simulationTime: time, eventType: "PROCESS_STARTED", itemId, stageId: stage, resourcePoolId: `${stage}-pool` });
      time += 2;
      events.push({ sequence: sequence++, simulationTime: time, eventType: "PROCESS_COMPLETED", itemId, stageId: stage });
      events.push({ sequence: sequence++, simulationTime: time, eventType: "RESOURCE_RELEASED", itemId, resourcePoolId: `${stage}-pool` });
    }
    events.push({ sequence: sequence++, simulationTime: time + 1, eventType: "ITEM_COMPLETED", itemId });
  }
  return events.slice(0, eventCount);
}

const matrices = [
  { items: 10, targetEvents: 100 },
  { items: 25, targetEvents: 500 },
  { items: 25, targetEvents: 1000 },
  { items: 50, targetEvents: 2000 },
];

const rows = [];
for (const { items, targetEvents } of matrices) {
  const raw = generateFixture(items, targetEvents);
  const normalizeStart = performance.now();
  const { events, warnings } = normalizeEvents(raw);
  const normalizeMs = performance.now() - normalizeStart;

  const timelineStart = performance.now();
  const timeline = buildTimeline(events);
  const timelineMs = performance.now() - timelineStart;

  const seekStart = performance.now();
  const midpoint = events.length ? events[Math.floor(events.length / 2)].simulationTime : 0;
  let low = 0, high = timeline.checkpoints.length - 1, found = -1;
  while (low <= high) { const mid = (low + high) >> 1; if (timeline.checkpoints[mid].simulationTime <= midpoint) { found = mid; low = mid + 1; } else high = mid - 1; }
  const seekMs = performance.now() - seekStart;

  const presentationBytes = Buffer.byteLength(JSON.stringify(events));
  const exportBytes = Buffer.byteLength(JSON.stringify({ events, checkpoints: timeline.checkpoints }));

  rows.push({
    items, events: events.length, normalizeMs: Number(normalizeMs.toFixed(3)), timelineMs: Number(timelineMs.toFixed(3)),
    checkpointCount: timeline.checkpoints.length, seekMs: Number(seekMs.toFixed(3)), presentationBytes, exportBytes, warnings: warnings.length,
  });
  console.log(`items=${items} events=${events.length} normalize=${normalizeMs.toFixed(2)}ms timeline=${timelineMs.toFixed(2)}ms seek=${seekMs.toFixed(3)}ms presentationBytes=${presentationBytes} exportBytes=${exportBytes} warnings=${warnings.length}`);
}

const table = [
  "# Playback Performance",
  "",
  "Local measurements only; no simulation rerun and no network request occur in this benchmark. Measured functions mirror `apps/web/lib/playback/normalize.ts` and `apps/web/lib/playback/timeline.ts` (see the script header).",
  "",
  "| Items | Events | Normalization (ms) | Timeline construction (ms) | Checkpoints | Seek (ms) | Presentation bytes | Export bytes | Warnings |",
  "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
  ...rows.map((row) => `| ${row.items} | ${row.events} | ${row.normalizeMs} | ${row.timelineMs} | ${row.checkpointCount} | ${row.seekMs} | ${row.presentationBytes} | ${row.exportBytes} | ${row.warnings} |`),
  "",
].join("\n");

writeFileSync(outputPath, table);
console.log(`Recorded -> ${outputPath}`);
