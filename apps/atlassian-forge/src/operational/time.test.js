import assert from "node:assert/strict";
import test from "node:test";
import { observationWindow, reviewedObservationWindow } from "./time.js";

test("reviewed windows must match the authorized duration and stay in the past", () => {
  const now = new Date("2026-10-15T01:00:00.000Z");
  const window = observationWindow(30, new Date("2026-10-15T00:00:00.000Z"));
  const accepted = reviewedObservationWindow(window, now);
  assert.equal(accepted.error, undefined);
  assert.equal(accepted.window.start, window.start);
  assert.equal(reviewedObservationWindow({ ...window, windowDays: 60 }, now).error.includes("duration"), true);
  assert.equal(
    reviewedObservationWindow(observationWindow(30, new Date("2026-10-15T02:00:00.000Z")), now).error.includes("future"),
    true,
  );
});
