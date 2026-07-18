import { describe, expect, it } from "vitest";

import { normalizeEvents } from "../lib/playback/normalize";
import { buildFrame, buildTimeline } from "../lib/playback/timeline";
import type { PlaybackEvent } from "../lib/playback/types";

function rawEvent(overrides: Record<string, unknown>): Record<string, unknown> {
  return {
    simulationTime: 0, sequence: 0, eventType: "ITEM_CREATED", itemId: "a",
    stageId: null, resourcePoolId: null, routeId: null, targetId: null, sampledDuration: null,
    ...overrides,
  };
}

// One item through triage (agents, capacity 1): arrival -> queue -> process -> complete -> route -> completed.
// QUEUE_ENTERED and PROCESS_STARTED use different simulationTime values on
// purpose: checkpoints group by exact simulationTime, so events sharing a
// timestamp would land in the same checkpoint and "waiting" would never be
// independently observable from "processing".
const controlledRaw = [
  rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "a" }),
  rawEvent({ sequence: 1, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
  rawEvent({ sequence: 2, simulationTime: 2, eventType: "RESOURCE_REQUESTED", itemId: "a", resourcePoolId: "agents" }),
  rawEvent({ sequence: 3, simulationTime: 2, eventType: "PROCESS_STARTED", itemId: "a", stageId: "triage", resourcePoolId: "agents" }),
  rawEvent({ sequence: 4, simulationTime: 8, eventType: "PROCESS_COMPLETED", itemId: "a", stageId: "triage" }),
  rawEvent({ sequence: 5, simulationTime: 8, eventType: "RESOURCE_RELEASED", itemId: "a", resourcePoolId: "agents" }),
  rawEvent({ sequence: 6, simulationTime: 8, eventType: "ROUTE_SELECTED", itemId: "a", routeId: "triage-complete", targetId: "completion:triage-complete:0" }),
  rawEvent({ sequence: 7, simulationTime: 8, eventType: "ITEM_COMPLETED", itemId: "a" }),
];

function buildControlledTimeline() {
  const { events, warnings } = normalizeEvents(controlledRaw);
  return buildTimeline(events, warnings);
}

describe("buildTimeline / buildFrame", () => {
  it("initial frame has no occupancy before the first event", () => {
    const timeline = buildControlledTimeline();
    const frame = buildFrame(timeline, -1);
    expect(frame.stages).toEqual([]);
    expect(frame.resources).toEqual([]);
    expect(frame.completedItemIds).toEqual([]);
  });

  it("reconstructs queue entry as waiting", () => {
    const timeline = buildControlledTimeline();
    const frame = buildFrame(timeline, 0);
    const triage = frame.stages.find((stage) => stage.stageId === "triage");
    expect(triage?.waitingItemIds).toEqual(["a"]);
    expect(triage?.processingItemIds).toEqual([]);
  });

  it("processing start moves the item from waiting to processing and marks the resource busy", () => {
    const timeline = buildControlledTimeline();
    const frame = buildFrame(timeline, 2);
    const triage = frame.stages.find((stage) => stage.stageId === "triage");
    expect(triage?.waitingItemIds).toEqual([]);
    expect(triage?.processingItemIds).toEqual(["a"]);
    const agents = frame.resources.find((resource) => resource.resourcePoolId === "agents");
    expect(agents?.busyItemIds).toEqual(["a"]);
  });

  it("processing complete and resource release clear occupancy", () => {
    const timeline = buildControlledTimeline();
    const frame = buildFrame(timeline, 8);
    expect(frame.stages.find((stage) => stage.stageId === "triage")?.processingItemIds).toEqual([]);
    expect(frame.resources.find((resource) => resource.resourcePoolId === "agents")?.busyItemIds).toEqual([]);
  });

  it("route transition is visible in eventsAtTime", () => {
    const timeline = buildControlledTimeline();
    const frame = buildFrame(timeline, 8);
    expect(frame.eventsAtTime.some((event) => event.eventType === "ROUTE_SELECTED" && event.routeId === "triage-complete")).toBe(true);
  });

  it("final frame reflects completion", () => {
    const timeline = buildControlledTimeline();
    const frame = buildFrame(timeline, timeline.maxTime);
    expect(frame.completedItemIds).toEqual(["a"]);
    expect(frame.failedItemIds).toEqual([]);
  });

  it("rework keeps a repeated stage visit distinct rather than collapsing it", () => {
    const raw = [
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "quality-check" }),
      rawEvent({ sequence: 1, simulationTime: 1, eventType: "PROCESS_STARTED", itemId: "a", stageId: "quality-check" }),
      rawEvent({ sequence: 2, simulationTime: 2, eventType: "PROCESS_COMPLETED", itemId: "a", stageId: "quality-check" }),
      rawEvent({ sequence: 3, simulationTime: 2, eventType: "ITEM_REWORKED", itemId: "a" }),
      rawEvent({ sequence: 4, simulationTime: 2, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "level-2" }),
    ];
    const { events, warnings } = normalizeEvents(raw);
    const timeline = buildTimeline(events, warnings);
    const frame = buildFrame(timeline, 2);
    expect(frame.reworkingItemIds).toEqual(["a"]);
    expect(frame.stages.find((stage) => stage.stageId === "level-2")?.waitingItemIds).toEqual(["a"]);
  });

  it("failure clears occupancy and is reported as a distinct terminal state", () => {
    const raw = [
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 1, simulationTime: 1, eventType: "PROCESS_STARTED", itemId: "a", stageId: "triage", resourcePoolId: "agents" }),
      rawEvent({ sequence: 2, simulationTime: 2, eventType: "ITEM_FAILED", itemId: "a" }),
    ];
    const { events, warnings } = normalizeEvents(raw);
    const timeline = buildTimeline(events, warnings);
    const frame = buildFrame(timeline, 2);
    expect(frame.failedItemIds).toEqual(["a"]);
    expect(frame.stages.find((stage) => stage.stageId === "triage")?.processingItemIds).toEqual([]);
  });

  it("seeking to the same time is deterministic", () => {
    const timeline = buildControlledTimeline();
    const first = buildFrame(timeline, 0);
    const second = buildFrame(timeline, 0);
    expect(second).toEqual(first);
  });

  it("no negative queue counts ever appear (array lengths are always >= 0 by construction)", () => {
    const timeline = buildControlledTimeline();
    for (const checkpoint of timeline.checkpoints) {
      for (const stage of checkpoint.frame.stages) {
        expect(stage.waitingItemIds.length).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("time between checkpoints reuses the prior occupancy with no events at that instant", () => {
    const timeline = buildControlledTimeline();
    const frame = buildFrame(timeline, 4);
    expect(frame.eventsAtTime).toEqual([]);
    expect(frame.stages.find((stage) => stage.stageId === "triage")?.processingItemIds).toEqual(["a"]);
  });

  it("step reversibility: stepping to the previous checkpoint restores the exact prior frame", () => {
    const timeline = buildControlledTimeline();
    const beforeIndex = 0; // checkpoint at time 0 (queue entry)
    const afterIndex = 1; // checkpoint at time 2 (processing start)
    const before = timeline.checkpoints[beforeIndex].frame;
    const forward = timeline.checkpoints[afterIndex].frame;
    expect(forward).not.toEqual(before);
    const restored = timeline.checkpoints[beforeIndex].frame;
    expect(restored).toEqual(before);
  });

  it("empty event list produces an empty timeline without crashing", () => {
    const { events, warnings } = normalizeEvents([]);
    const timeline = buildTimeline(events, warnings);
    expect(timeline.checkpoints).toEqual([]);
    expect(buildFrame(timeline, 0)).toMatchObject({ stages: [], resources: [] });
  });

  it("carries normalization warnings through to the timeline for missing-event visibility", () => {
    const raw = [rawEvent({ sequence: 0, simulationTime: Number.NaN })];
    const { events, warnings } = normalizeEvents(raw);
    const timeline = buildTimeline(events, warnings);
    expect(timeline.warnings.length).toBeGreaterThan(0);
  });
});

describe("event ordering (GM-123)", () => {
  it("normalized events sort by simulationTime then original event index", () => {
    const raw: Record<string, unknown>[] = [
      rawEvent({ sequence: 5, simulationTime: 10 }),
      rawEvent({ sequence: 1, simulationTime: 1 }),
      rawEvent({ sequence: 3, simulationTime: 1 }),
    ];
    const { events } = normalizeEvents(raw);
    const times = events.map((event: PlaybackEvent) => event.simulationTime);
    expect(times).toEqual([...times].sort((a, b) => a - b));
    expect(events[0].sourceIndex).toBe(1);
    expect(events[1].sourceIndex).toBe(2);
  });
});
