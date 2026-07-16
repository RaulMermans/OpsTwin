import { describe, expect, it } from "vitest";

import { buildCsvExport, buildJsonExport, sanitizeForExport } from "../lib/scenario-lab/exports";

const result = {
  schemaVersion: "0.5.0",
  objective: { metric: "averageCycleTime" },
  scenarios: [{
    scenarioId: "staffing",
    scenarioName: "Add staffing",
    status: "valid",
    eligible: true,
    pairedRunCount: 10,
    pairedMetrics: { averageCycleTime: { absoluteDelta: { mean: -2 }, relativeDelta: { mean: -0.1 }, improvement: { probabilityOfImprovement: 0.8, probabilityOfDegradation: 0.2 } } },
    guardrails: [],
    riskComparisons: [],
    privatePath: "C:\\private\\file",
    events: [{ secret: "event" }],
  }],
  ranking: [{ scenarioId: "staffing", rank: 1 }],
  representatives: { baseline: { representative: { result: { events: [{ id: 1 }] } } } },
  integrity: { status: "passed", checksRun: 16 },
};

describe("Scenario Lab exports", () => {
  it("recursively excludes event logs and unsafe keys", () => {
    const cleaned = sanitizeForExport({ events: [1], stack: "private", password: "secret", nested: { returnedEvents: [2], value: 3 } });
    expect(cleaned).toEqual({ nested: { value: 3 } });
  });

  it("creates a versioned JSON artifact without event evidence or paths", () => {
    const json = buildJsonExport({ baseline: { slaTarget: 60 }, scenarios: [], settings: { runs: 10 }, result, timestamp: "2026-07-16T12:00:00.000Z" });
    expect(json).toContain('"exportVersion": "1.0.0"');
    expect(json).not.toMatch(/events|privatePath|C:\\\\private/i);
  });

  it("creates stable CSV headers and one row per scenario", () => {
    const csv = buildCsvExport(result);
    expect(csv.split("\n")[0]).toBe("scenario_id,scenario_name,status,rank,objective,objective_mean_delta,relative_delta,probability_improved,probability_degraded,guardrail_status,paired_runs,baseline_risk,scenario_risk");
    expect(csv).toContain("staffing,Add staffing,Ranked,1,averageCycleTime,-2,-0.1,0.8,0.2,No guardrails configured,10,,");
  });

  it("quotes CSV cells containing commas or quotes", () => {
    const quoted = { ...result, scenarios: [{ ...result.scenarios[0], scenarioName: 'Staffing, "plus"' }] };
    expect(buildCsvExport(quoted)).toContain('"Staffing, ""plus"""');
  });
});
