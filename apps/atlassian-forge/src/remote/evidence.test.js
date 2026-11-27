import assert from "node:assert/strict";
import test from "node:test";
import { validateTransformEvidence } from "./evidence.js";

test("malformed cg5 responses are rejected", () => {
  const rejected = validateTransformEvidence({
    contractVersion: "cg5.v1",
    synthetic: true,
    identitiesAgree: true,
    experimentStatus: "complete",
    alternatives: [{ alternativeId: "human-expansion", status: "valid", systemMetrics: { averageCycleTime: { mean: Number.NaN } } }],
  });
  assert.equal(rejected.ok, false);
});

test("stale request identities are rejected", () => {
  const rejected = validateTransformEvidence(
    {
      contractVersion: "cg5.v1",
      synthetic: true,
      identitiesAgree: true,
      experimentStatus: "complete",
      requestId: "old",
      experimentId: "exp-1",
      alternatives: [
        {
          alternativeId: "human-expansion",
          status: "valid",
          systemMetrics: { averageCycleTime: { mean: 12, unit: "minutes" } },
          probabilityOfImprovement: 0.6,
          validPairedRunCount: 2,
        },
      ],
      integrityStatus: "passed",
    },
    { requestId: "new", experimentId: "exp-1" },
  );
  assert.equal(rejected.ok, false);
});

test("complete experiments cannot hide failed alternatives", () => {
  const rejected = validateTransformEvidence({
    contractVersion: "cg5.v1",
    synthetic: true,
    identitiesAgree: true,
    experimentStatus: "complete",
    alternatives: [{ alternativeId: "hybrid", status: "failed", message: "unsupported" }],
    integrityStatus: "passed",
  });
  assert.equal(rejected.ok, false);
});
