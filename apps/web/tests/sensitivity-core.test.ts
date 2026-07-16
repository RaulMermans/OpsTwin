import { describe, expect, it } from "vitest";

import { buildSensitivityRequest, parseSensitivityValues } from "../lib/sensitivity/request-adapter";
import { isSensitivityResult } from "../lib/api/simulation";
import { DEFAULT_FORM, buildBaseline } from "../lib/templates/support";

describe("sensitivity request adapter", () => {
  it("builds the default Level 1 capacity request", () => {
    const payload = buildSensitivityRequest(buildBaseline({ ...DEFAULT_FORM }), {
      targetKey: "level1Capacity", values: [2, 3, 4, 5], runs: 50, metric: "averageCycleTime",
    });

    expect(payload).toMatchObject({
      schemaVersion: "0.6.0",
      target: { entityType: "resourcePool", entityId: "level-1-agents", field: "capacity" },
      values: [2, 3, 4, 5],
      execution: { runCount: 50 },
      metrics: ["averageCycleTime"],
    });
  });

  it("rejects duplicate and non-finite explicit values", () => {
    expect(parseSensitivityValues("2, 3, 3")).toEqual({ values: [], error: "Tested values must be distinct." });
    expect(parseSensitivityValues("2, nope, 4").error).toMatch(/numbers/i);
  });

  it("rejects shallow or non-finite sensitivity responses", () => {
    const base = {
      schemaVersion: "0.6.0", baselineModelHash: "a".repeat(64),
      target: { entityType: "resourcePool", entityId: "agents", field: "capacity", label: "Capacity", unit: "workers", valueType: "integer", baselineValue: 1 },
      originalValues: [1, 2], canonicalValues: [1, 2], requestedRunCount: 2, baseSeed: 42,
      seedScheduleAlgorithm: "sha256_first_64_bits", runSeeds: [{ runIndex: 0, seed: 1 }, { runIndex: 1, seed: 2 }], confidenceLevel: 0.95,
      workBudget: { baselineItemCount: 1, runCount: 2, testedValueCount: 2, estimatedWorkUnits: 4, maximumWorkUnits: 100000 },
      values: [], responseCurves: [{ metric: "averageCycleTime", unit: "minutes", direction: "minimize", points: [{ parameterValue: 1, isBaselineValue: true, status: "valid", mean: 1, confidenceIntervalLower: 1, confidenceIntervalUpper: 1, observedElasticity: null }], finiteDifferences: [], monotonicity: "insufficient_evidence", thresholdCrossings: [] }],
      execution: { executionOrder: "run_index_then_values", ordinarySimulationExecutions: 4, ordinaryRunIncludedEventCount: 0, ordinaryRunRetainedEventCount: 0 },
      integrity: { status: "passed", checksRun: 24 },
    };
    expect(isSensitivityResult(base)).toBe(true);
    expect(isSensitivityResult({ ...base, responseCurves: [{}] })).toBe(false);
    expect(isSensitivityResult({ ...base, canonicalValues: [1, Number.NaN] })).toBe(false);
  });
});
