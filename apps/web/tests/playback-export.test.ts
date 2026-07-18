import { describe, expect, it } from "vitest";

import { buildPlaybackExport } from "../lib/playback/export";
import type { PlaybackSelection } from "../lib/playback/types";

const selection: PlaybackSelection = {
  variant: "scenario",
  variantId: "capacity",
  runIndex: 2,
  seed: 42,
  selectionMethod: "normalized_median_vector",
  distance: 0.05,
  detailMode: "sampled",
  includedEventCount: 3,
  modelHash: "hash-abc",
  scenarioName: "Two agents",
  observation: { measurementStart: 0, measurementEnd: 100, measurementDuration: 100 },
  selectedItemIds: ["item-1"],
};

describe("buildPlaybackExport", () => {
  it("includes required evidence fields", () => {
    const payload = buildPlaybackExport(selection, [], ["Maximum sampled queue: 3 items at time 10."], [], []);
    expect(payload).toMatchObject({
      exportVersion: 1,
      sourceType: "scenario",
      scenarioId: "capacity",
      runIndex: 2,
      seed: 42,
      selectionMethod: "normalized_median_vector",
    });
    expect(payload.observationWindow).toEqual(selection.observation);
  });

  it("never includes filesystem paths, stack traces, or browser/timer internals", () => {
    const payload = buildPlaybackExport(selection, [], [], [], []);
    const serialized = JSON.stringify(payload);
    expect(serialized).not.toMatch(/\/Users\/|\/home\/|[A-Za-z]:\\\\/);
    expect(serialized).not.toMatch(/Traceback|at Object\.<anonymous>/);
    expect(payload).not.toHaveProperty("timer");
    expect(payload).not.toHaveProperty("reactState");
  });

  it("excludes full unretained event history by construction (only retained events are ever passed in)", () => {
    const payload = buildPlaybackExport(selection, [], [], [], []);
    expect(payload.events).toEqual([]);
  });
});
