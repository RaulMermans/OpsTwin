import { describe, expect, it } from "vitest";

import { deriveImportantEvents, nextImportantEventIndex, previousImportantEventIndex } from "../lib/playback/important-events";
import { normalizeEvents } from "../lib/playback/normalize";
import { buildTimeline } from "../lib/playback/timeline";

function rawEvent(overrides: Record<string, unknown>): Record<string, unknown> {
  return {
    simulationTime: 0, sequence: 0, eventType: "ITEM_CREATED", itemId: "a",
    stageId: null, resourcePoolId: null, routeId: null, targetId: null, sampledDuration: null,
    ...overrides,
  };
}

function timelineFrom(raw: Record<string, unknown>[]) {
  const { events, warnings } = normalizeEvents(raw);
  return buildTimeline(events, warnings);
}

describe("deriveImportantEvents", () => {
  it("reports a resource reaching and leaving full utilization", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 1, simulationTime: 1, eventType: "PROCESS_STARTED", itemId: "a", stageId: "triage", resourcePoolId: "agents" }),
      rawEvent({ sequence: 2, simulationTime: 5, eventType: "PROCESS_COMPLETED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 3, simulationTime: 5, eventType: "RESOURCE_RELEASED", itemId: "a", resourcePoolId: "agents" }),
    ]);
    const important = deriveImportantEvents(timeline, { agents: 1 });
    expect(important.some((item) => item.category === "resource_fully_utilized" && item.simulationTime === 1)).toBe(true);
    expect(important.some((item) => item.category === "resource_no_longer_fully_utilized" && item.simulationTime === 5)).toBe(true);
  });

  it("records the maximum sampled queue only when a new maximum is reached", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 1, simulationTime: 1, eventType: "QUEUE_ENTERED", itemId: "b", stageId: "triage" }),
      rawEvent({ sequence: 2, simulationTime: 2, eventType: "PROCESS_STARTED", itemId: "a", stageId: "triage" }),
    ]);
    const important = deriveImportantEvents(timeline, {});
    const queueEvents = important.filter((item) => item.category === "maximum_sampled_queue_reached");
    expect(queueEvents).toHaveLength(2);
    expect(queueEvents[1].summary).toContain("2 items");
  });

  it("reports rework, failure, and completion as important events", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 1, eventType: "ITEM_REWORKED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 2, eventType: "ITEM_FAILED", itemId: "b" }),
      rawEvent({ sequence: 2, simulationTime: 3, eventType: "ITEM_COMPLETED", itemId: "c" }),
    ]);
    const important = deriveImportantEvents(timeline, {});
    expect(important.map((item) => item.category)).toEqual(["rework_started", "item_failed", "item_completed"]);
  });

  it("navigates to the next and previous important event index", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 1, eventType: "ITEM_FAILED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 2, eventType: "ITEM_COMPLETED", itemId: "b" }),
    ]);
    const important = deriveImportantEvents(timeline, {});
    expect(nextImportantEventIndex(important, -1)).toBe(important[0].eventIndex);
    expect(nextImportantEventIndex(important, important[1].eventIndex)).toBeNull();
    expect(previousImportantEventIndex(important, important[1].eventIndex)).toBe(important[0].eventIndex);
    expect(previousImportantEventIndex(important, important[0].eventIndex)).toBeNull();
  });

  it("only derives events from available sampled evidence (no capacity means no utilization events)", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 1, eventType: "PROCESS_STARTED", itemId: "a", resourcePoolId: "unknown-pool" }),
    ]);
    const important = deriveImportantEvents(timeline, {});
    expect(important.some((item) => item.category.startsWith("resource_"))).toBe(false);
  });
});
