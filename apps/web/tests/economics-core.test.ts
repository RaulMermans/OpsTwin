import { describe, expect, it } from "vitest";
import { buildEconomicCsvExport, buildEconomicJsonExport } from "../lib/economics/exports";
import { buildEconomicAssumptions, DEFAULT_ECONOMIC_DRAFT, interventionFor, validateEconomicDraft } from "../lib/economics/request-adapter";

describe("economic request mapping", () => {
  it("omits blank assumptions and preserves configured zero", () => {
    const assumptions = buildEconomicAssumptions({ ...DEFAULT_ECONOMIC_DRAFT, level1CapacityRate: "0", level2CapacityRate: "", fixedPeriodCost: "" });
    expect(assumptions.resourceProvisioning).toEqual([{ resourcePoolId: "level-1-agents", costPerCapacityTimeUnit: 0 }]);
    expect(assumptions).not.toHaveProperty("fixedCostPerAnalysisPeriod");
  });
  it("rejects negative values and validates explicit amortization", () => {
    expect(validateEconomicDraft({ ...DEFAULT_ECONOMIC_DRAFT, reworkRate: "-1" })).toMatch(/at least zero/i);
    expect(interventionFor("scenario-1", "120", "12")).toEqual({ scenarioId: "scenario-1", oneTimeCost: 120, amortizationPeriods: 12 });
  });
});

describe("economic exports", () => {
  const result = { schemaVersion: "0.7.0", currency: "EUR", scenarios: [{ scenarioId: "s1", scenarioName: "Capacity", baselineCost: { recurringOperatingCost: { mean: 10 } }, scenarioCost: { recurringOperatingCost: { mean: 12 }, costPerCompletedItem: { mean: 2 } }, recurringCostDelta: { absoluteDelta: { mean: 2 }, relativeDelta: { mean: .2 } }, probabilityLowerCost: .1, objectiveMetric: "averageCycleTime", objectiveMeanPairedDelta: -1, probabilityOperationallyImproved: .8, tradeoffClassification: "higher_cost_and_improved", intervention: { oneTimeCost: 120, amortizedCostPerPeriod: 10 }, economicGuardrails: [], pairedRunCount: 10 }], events: [{ secret: "excluded" }] };
  it("uses the documented CSV columns", () => { expect(buildEconomicCsvExport(result).split("\n")[0]).toContain("tradeoff_classification"); });
  it("removes event evidence from JSON", () => { expect(buildEconomicJsonExport(result)).not.toContain("excluded"); });
});
