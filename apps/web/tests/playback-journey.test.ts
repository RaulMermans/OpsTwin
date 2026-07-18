import { describe, expect, it } from "vitest";

import { normalizeEvents } from "../lib/playback/normalize";
import { buildItemJourney } from "../lib/playback/journey";
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

describe("buildItemJourney", () => {
  it("reconstructs a normal completion with waiting and processing durations", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 2, simulationTime: 2, eventType: "PROCESS_STARTED", itemId: "a", stageId: "triage", resourcePoolId: "agents" }),
      rawEvent({ sequence: 3, simulationTime: 10, eventType: "PROCESS_COMPLETED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 4, simulationTime: 10, eventType: "ROUTE_SELECTED", itemId: "a", routeId: "triage-complete", targetId: "completion:triage-complete:0" }),
      rawEvent({ sequence: 5, simulationTime: 10, eventType: "ITEM_COMPLETED", itemId: "a" }),
    ]);
    const journey = buildItemJourney(timeline, "a", 30);
    expect(journey.arrivalTime).toBe(0);
    expect(journey.completedAt).toBe(10);
    expect(journey.failedAt).toBeNull();
    expect(journey.cycleTime).toBe(10);
    expect(journey.visits).toHaveLength(1);
    expect(journey.visits[0]).toMatchObject({ stageId: "triage", waitingDuration: 2, processingDuration: 8, reworked: false });
    expect(journey.routeDecisions).toEqual([{ routeId: "triage-complete", targetId: "completion:triage-complete:0", simulationTime: 10 }]);
    expect(journey.slaResult).toBe("attained");
  });

  it("reconstructs a failure with no completion", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 2, simulationTime: 1, eventType: "PROCESS_STARTED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 3, simulationTime: 5, eventType: "ITEM_FAILED", itemId: "a" }),
    ]);
    const journey = buildItemJourney(timeline, "a", 30);
    expect(journey.completedAt).toBeNull();
    expect(journey.failedAt).toBe(5);
    expect(journey.cycleTime).toBe(5);
    expect(journey.slaResult).toBe("violated");
    expect(journey.visits[0].processCompletedAt).toBeNull();
  });

  it("keeps a rework loop as two distinct, ordered stage visits", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "quality-check" }),
      rawEvent({ sequence: 2, simulationTime: 1, eventType: "PROCESS_STARTED", itemId: "a", stageId: "quality-check" }),
      rawEvent({ sequence: 3, simulationTime: 2, eventType: "PROCESS_COMPLETED", itemId: "a", stageId: "quality-check" }),
      rawEvent({ sequence: 4, simulationTime: 2, eventType: "ITEM_REWORKED", itemId: "a" }),
      rawEvent({ sequence: 5, simulationTime: 2, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "level-2" }),
      rawEvent({ sequence: 6, simulationTime: 3, eventType: "PROCESS_STARTED", itemId: "a", stageId: "level-2" }),
      rawEvent({ sequence: 7, simulationTime: 6, eventType: "PROCESS_COMPLETED", itemId: "a", stageId: "level-2" }),
      rawEvent({ sequence: 8, simulationTime: 6, eventType: "ITEM_COMPLETED", itemId: "a" }),
    ]);
    const journey = buildItemJourney(timeline, "a", 30);
    expect(journey.reworkCount).toBe(1);
    expect(journey.visits.map((visit) => visit.stageId)).toEqual(["quality-check", "level-2"]);
    expect(journey.visits[0].reworked).toBe(true);
    expect(journey.visits[0].visitNumber).toBe(1);
    expect(journey.visits[1].visitNumber).toBe(2);
  });

  it("reports missing events as unavailable rather than inventing them", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
    ]);
    const journey = buildItemJourney(timeline, "a", 30);
    expect(journey.arrivalTime).toBeNull();
    expect(journey.completedAt).toBeNull();
    expect(journey.slaResult).toBe("not_available");
  });

  it("reports SLA violation when cycle time exceeds the target duration", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 40, eventType: "ITEM_COMPLETED", itemId: "a" }),
    ]);
    const journey = buildItemJourney(timeline, "a", 30);
    expect(journey.slaResult).toBe("violated");
  });

  it("returns not_available when no SLA target duration is supplied", () => {
    const timeline = timelineFrom([
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 5, eventType: "ITEM_COMPLETED", itemId: "a" }),
    ]);
    const journey = buildItemJourney(timeline, "a", null);
    expect(journey.slaResult).toBe("not_available");
  });
});
