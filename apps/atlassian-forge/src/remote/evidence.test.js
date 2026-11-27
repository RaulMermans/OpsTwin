import assert from "node:assert/strict";
import test from "node:test";
import { validateEconomicEvidence, validateTransformEvidence } from "./evidence.js";

test("complete experiments require passed integrity and identity", () => {
  const rejected = validateTransformEvidence({
    contractVersion: "cg5.v1",
    synthetic: true,
    identitiesAgree: true,
    experimentStatus: "complete",
    experimentIdentity: "x".repeat(16),
    alternatives: [
      {
        alternativeId: "human-expansion",
        status: "valid",
        systemMetrics: { averageCycleTime: { mean: 12, unit: "minutes" } },
        probabilityOfImprovement: 0.6,
        validPairedRunCount: 2,
      },
    ],
    integrityStatus: "failed",
  });
  assert.equal(rejected.ok, false);
});

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
      experimentIdentity: "x".repeat(16),
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

test("economic results must stay bound to the operational experiment", () => {
  const rejected = validateEconomicEvidence(
    {
      contractVersion: "cg6.v1",
      synthetic: true,
      integrityStatus: "passed",
      operationalExperimentIdentity: "other",
      strategies: [{ strategyId: "hybrid", incrementalInvestment: 1, roi: 0.1 }],
    },
    { experimentIdentity: "expected" },
  );
  assert.equal(rejected.ok, false);
});
