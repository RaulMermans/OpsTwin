import assert from "node:assert/strict";
import test from "node:test";
import { generateSynthetic } from "./synthetic.js";

test("the same seed reproduces canonical content", () => {
  const a = generateSynthetic("medium", 99, new Date("2026-10-15T00:00:00.000Z"));
  const b = generateSynthetic("medium", 99, new Date("2026-10-15T00:00:00.000Z"));
  assert.equal(a.contentFingerprint, b.contentFingerprint);
});

test("different seeds vary medium datasets", () => {
  const a = generateSynthetic("medium", 1, new Date("2026-10-15T00:00:00.000Z"));
  const b = generateSynthetic("medium", 2, new Date("2026-10-15T00:00:00.000Z"));
  assert.notEqual(a.contentFingerprint, b.contentFingerprint);
});

test("stress profile remains synthetic and includes quality failures or warnings", () => {
  const snapshot = generateSynthetic("stress", 7, new Date("2026-10-15T00:00:00.000Z"));
  assert.equal(snapshot.provenance.evidenceClass, "synthetic");
  assert.ok(snapshot.dataQuality.some((item) => item.status === "fail" || item.status === "warning"));
});
