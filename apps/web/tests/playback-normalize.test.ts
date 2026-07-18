import { describe, expect, it } from "vitest";

import { extractRepresentativeSource, normalizeEvents } from "../lib/playback/normalize";

function rawEvent(overrides: Record<string, unknown>): Record<string, unknown> {
  return {
    simulationTime: 0,
    sequence: 0,
    eventType: "ITEM_CREATED",
    itemId: "item-1",
    sourceId: "tickets",
    stageId: null,
    resourcePoolId: null,
    routeId: null,
    targetId: null,
    priority: 0,
    attempt: null,
    sampledDuration: null,
    reason: null,
    ...overrides,
  };
}

describe("normalizeEvents", () => {
  it("sorts by simulationTime then original event index for equal timestamps", () => {
    const raw = [
      rawEvent({ sequence: 2, simulationTime: 5, itemId: "b" }),
      rawEvent({ sequence: 0, simulationTime: 5, itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 2, itemId: "c" }),
    ];
    const { events } = normalizeEvents(raw);
    expect(events.map((event) => event.itemId)).toEqual(["c", "b", "a"]);
    expect(events.map((event) => event.index)).toEqual([0, 1, 2]);
  });

  it("preserves stable ordering for a realistic multi-item sequence", () => {
    const raw = [
      rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "a" }),
      rawEvent({ sequence: 1, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "a", stageId: "triage" }),
      rawEvent({ sequence: 2, simulationTime: 3, eventType: "PROCESS_STARTED", itemId: "a", stageId: "triage", resourcePoolId: "agents" }),
    ];
    const { events } = normalizeEvents(raw);
    expect(events.map((event) => event.eventType)).toEqual(["ITEM_CREATED", "QUEUE_ENTERED", "PROCESS_STARTED"]);
  });

  it("rejects duplicate event IDs and warns", () => {
    const raw = [
      rawEvent({ sequence: 7, simulationTime: 0, itemId: "a" }),
      rawEvent({ sequence: 7, simulationTime: 1, itemId: "b" }),
    ];
    const { events, warnings } = normalizeEvents(raw);
    expect(events).toHaveLength(1);
    expect(events[0].itemId).toBe("a");
    expect(warnings).toContainEqual(expect.objectContaining({ code: "duplicate_event_id" }));
  });

  it("rejects non-finite simulation times and warns", () => {
    const raw = [
      rawEvent({ sequence: 0, simulationTime: Number.NaN }),
      rawEvent({ sequence: 1, simulationTime: Number.POSITIVE_INFINITY }),
      rawEvent({ sequence: 2, simulationTime: 4 }),
    ];
    const { events, warnings } = normalizeEvents(raw);
    expect(events).toHaveLength(1);
    expect(warnings.filter((warning) => warning.code === "non_finite_time")).toHaveLength(2);
  });

  it("keeps unknown event types as a safe generic event with a warning", () => {
    const raw = [rawEvent({ sequence: 0, eventType: "SOMETHING_NEW" })];
    const { events, warnings } = normalizeEvents(raw);
    expect(events).toHaveLength(1);
    expect(events[0].eventType).toBe("UNKNOWN");
    expect(warnings).toContainEqual(expect.objectContaining({ code: "unknown_event_type" }));
  });

  it("does not mutate the source evidence", () => {
    const raw = [rawEvent({ sequence: 0 })];
    const before = structuredClone(raw);
    normalizeEvents(raw);
    expect(raw).toEqual(before);
  });

  it("excludes events with a missing item ID and warns", () => {
    const raw = [rawEvent({ sequence: 0, itemId: null })];
    const { events, warnings } = normalizeEvents(raw);
    expect(events).toHaveLength(0);
    expect(warnings).toContainEqual(expect.objectContaining({ code: "missing_item_id" }));
  });
});

describe("extractRepresentativeSource", () => {
  const validVariant = {
    variantId: "baseline",
    representative: {
      runIndex: 3,
      seed: 42,
      selectionMethod: "normalized_median_vector",
      distance: 0.1,
      detailMode: "sampled",
      includedEventCount: 2,
      result: {
        observation: { measurementStart: 0, measurementEnd: 100, measurementDuration: 100 },
        resultDetail: { selectedItemIds: ["item-1", "item-2"] },
        events: [rawEvent({ sequence: 0 })],
      },
    },
  };

  it("extracts a complete playback source from a valid representative", () => {
    const source = extractRepresentativeSource("baseline", validVariant, null, "hash-1");
    expect(source).not.toBeNull();
    expect(source?.selection).toMatchObject({
      variant: "baseline",
      variantId: "baseline",
      runIndex: 3,
      seed: 42,
      selectionMethod: "normalized_median_vector",
      detailMode: "sampled",
      modelHash: "hash-1",
      selectedItemIds: ["item-1", "item-2"],
    });
    expect(source?.events).toHaveLength(1);
  });

  it("returns null when the representative was not retained", () => {
    expect(extractRepresentativeSource("scenario", null, null, null)).toBeNull();
    expect(extractRepresentativeSource("scenario", {}, null, null)).toBeNull();
  });

  it("returns null when the events array is absent", () => {
    const broken = { variantId: "baseline", representative: { ...validVariant.representative, result: { observation: null, resultDetail: null } } };
    expect(extractRepresentativeSource("baseline", broken, null, null)).toBeNull();
  });
});
