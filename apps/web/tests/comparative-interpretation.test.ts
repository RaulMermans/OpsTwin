import { describe, expect, it } from "vitest";

import type { ComparisonResult } from "../lib/api/simulation";
import { buildComparativeInterpretation } from "../lib/scenario-lab/comparative-interpretation";

function fixture(objectiveMetric: string, direction: "minimize" | "maximize", scenarios: Record<string, unknown>[], ranking: Record<string, unknown>[]): ComparisonResult {
  return { objective: { metric: objectiveMetric, direction }, scenarios, ranking } as unknown as ComparisonResult;
}

const scenario = (id: string, name: string) => ({ scenarioId: id, scenarioName: name });
const rankingRow = (id: string, rank: number, delta: number, probability = 0.7, tieBreakExplanation = "directed mean delta, improvement probability, confidence width, scenario ID") => ({
  scenarioId: id, rank, objectiveMeanDelta: delta, probabilityOfImprovement: probability, tieBreakExplanation,
});

describe("buildComparativeInterpretation", () => {
  it("identifies the leader for a lower-is-better objective", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], [rankingRow("s1", 1, -5), rankingRow("s2", 2, -2)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation).toMatchObject({ kind: "leader", scenarioId: "s1", scenarioName: "Add one Level 1 agent", objectiveMeanDelta: -5, excludedCount: 0, totalCount: 2 });
  });

  it("identifies the leader for a higher-is-better objective", () => {
    const result = fixture("slaAttainment", "maximize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], [rankingRow("s1", 1, 0.08), rankingRow("s2", 2, 0.03)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation).toMatchObject({ kind: "leader", scenarioId: "s1", objectiveMeanDelta: 0.08 });
  });

  it("reports an exact tie between the top two ranked scenarios", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], [rankingRow("s1", 1, -3), rankingRow("s2", 2, -3)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation).toMatchObject({ kind: "tie", scenarioIds: ["s1", "s2"], objectiveMeanDelta: -3 });
  });

  it("reports a near tie within the centralized comparison tolerance", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], [rankingRow("s1", 1, -3), rankingRow("s2", 2, -3 + 5e-10)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation.kind).toBe("tie");
  });

  it("does not report a tie once the delta difference exceeds the tolerance", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], [rankingRow("s1", 1, -3), rankingRow("s2", 2, -2.999)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation.kind).toBe("leader");
  });

  it("handles one failed scenario by excluding it and reporting the remaining scenario alone", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], [rankingRow("s1", 1, -5)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation).toMatchObject({ kind: "singleEligibleScenario", scenarioId: "s1", excludedCount: 1, totalCount: 2 });
  });

  it("handles one ineligible (guardrail-failed) scenario the same way as a failed scenario", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], [rankingRow("s1", 1, -5)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation.kind).toBe("singleEligibleScenario");
    expect(interpretation.excludedCount).toBe(1);
  });

  it("reports no comparison when no scenario has successful paired evidence", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent"), scenario("s2", "Faster triage")], []);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation).toMatchObject({ kind: "noEligibleScenarios", excludedCount: 2, totalCount: 2 });
  });

  it("reports a single-scenario result when only one scenario was tested", () => {
    const result = fixture("averageCycleTime", "minimize", [scenario("s1", "Add one Level 1 agent")], [rankingRow("s1", 1, -5)]);
    const interpretation = buildComparativeInterpretation(result);
    expect(interpretation).toMatchObject({ kind: "singleEligibleScenario", scenarioId: "s1", excludedCount: 0, totalCount: 1 });
  });
});
