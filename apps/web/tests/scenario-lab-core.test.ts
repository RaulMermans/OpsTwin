import { describe, expect, it } from "vitest";

import {
  deleteScenario,
  duplicateScenario,
  moveScenario,
  renameScenario,
} from "../lib/scenario-lab/scenario-state";
import { buildGuardrail, validateGuardrail, type GuardrailDraft } from "../lib/scenario-lab/guardrails";
import { formatMetric, metricRegistry } from "../lib/scenario-lab/metrics";
import { asRecord, getScenarioStatus, guardrailCopy } from "../lib/scenario-lab/result-adapter";
import { isLatestRequest } from "../lib/scenario-lab/request-lifecycle";
import type { ScenarioDraft } from "../lib/scenarios/builders";

const scenarios: ScenarioDraft[] = [
  { id: "one", name: "One", type: "demand", value: 10 },
  { id: "two", name: "Two", type: "level1Staffing", value: 1 },
  { id: "three", name: "Three", type: "quality", value: 20 },
];

describe("Scenario Lab scenario management", () => {
  it("renames without changing identity or values", () => {
    const next = renameScenario(scenarios, "one", "Demand pulse");
    expect(next[0]).toEqual({ ...scenarios[0], name: "Demand pulse" });
    expect(scenarios[0].name).toBe("One");
  });

  it("rejects an empty rename", () => {
    expect(renameScenario(scenarios, "one", "   ")).toBe(scenarios);
  });

  it("duplicates configuration under a new stable identity and distinct name", () => {
    const next = duplicateScenario(scenarios.slice(0, 2), "one", () => "copy-id");
    expect(next).toHaveLength(3);
    expect(next[1]).toEqual({ ...scenarios[0], id: "copy-id", name: "One copy" });
    expect(new Set(next.map((item) => item.id)).size).toBe(3);
  });

  it("does not duplicate beyond the three-scenario UI limit", () => {
    expect(duplicateScenario(scenarios, "one", () => "copy-id")).toBe(scenarios);
  });

  it("deletes only the selected scenario", () => {
    expect(deleteScenario(scenarios, "two").map((item) => item.id)).toEqual(["one", "three"]);
  });

  it("moves display order without changing IDs", () => {
    expect(moveScenario(scenarios, "two", -1).map((item) => item.id)).toEqual(["two", "one", "three"]);
    expect(moveScenario(scenarios, "two", 1).map((item) => item.id)).toEqual(["one", "three", "two"]);
  });
});

describe("optional guardrail mapping", () => {
  it("omits a disabled guardrail", () => {
    expect(buildGuardrail({ enabled: false, metric: "slaAttainment", value: 80 })).toEqual([]);
  });

  it("maps percentage and direction from the metric", () => {
    expect(buildGuardrail({ enabled: true, metric: "slaAttainment", value: 80 })).toEqual([
      { metric: "slaAttainment", operator: "greaterThanOrEqual", value: 0.8 },
    ]);
  });

  it("maps a supported resource utilization guardrail", () => {
    expect(buildGuardrail({ enabled: true, metric: "resourcePoolUtilization", value: 90, resourcePoolId: "level-1-agents" })).toEqual([
      { metric: "resourcePoolUtilization", operator: "lessThanOrEqual", value: 0.9, resourcePoolId: "level-1-agents" },
    ]);
  });

  it("blocks invalid thresholds", () => {
    const draft: GuardrailDraft = { enabled: true, metric: "averageCycleTime", value: Number.NaN };
    expect(validateGuardrail(draft)).toMatch(/valid threshold/i);
  });

  it("distinguishes no guardrail, pass, and failure wording", () => {
    expect(guardrailCopy(asRecord({ guardrails: [] })!)).toBe("No guardrails configured");
    expect(guardrailCopy(asRecord({ guardrails: [{ passed: true }] })!)).toBe("Passed the configured guardrail");
    expect(guardrailCopy(asRecord({ guardrails: [{ passed: false }] })!)).toBe("Failed the configured guardrail");
  });
});

describe("metric presentation and statuses", () => {
  it("formats probabilities as percentages and durations with minutes", () => {
    expect(formatMetric("slaAttainment", 0.8123)).toBe("81.2%");
    expect(formatMetric("averageCycleTime", 12.345)).toBe("12.35 min");
  });

  it("does not turn missing or non-finite values into zero", () => {
    expect(formatMetric("averageCycleTime", null)).toBe("Not available");
    expect(formatMetric("averageCycleTime", Number.POSITIVE_INFINITY)).toBe("Not available");
  });

  it("keeps resource utilization direction neutral", () => {
    expect(metricRegistry.resourceUtilization.betterDirection).toBe("Contextual load");
  });

  it.each([
    [{ status: "valid", eligible: true }, { rank: 1 }, "Ranked"],
    [{ status: "valid", eligible: true }, null, "Eligible but unranked"],
    [{ status: "valid", eligible: false, guardrails: [{ passed: false }] }, null, "Ineligible - guardrail failed"],
    [{ status: "failed", failure: { category: "override_validation" } }, null, "Invalid scenario"],
    [{ status: "failed", failure: { category: "paired_execution" } }, null, "Execution failed"],
    [{ status: "failed", failure: { category: "paired_ratio_failure" } }, null, "Insufficient paired runs"],
    [{ status: "mystery" }, null, "Result unavailable"],
  ])("maps a safe primary status", (scenario, ranking, expected) => {
    expect(getScenarioStatus(scenario, ranking)).toBe(expected);
  });
});

describe("request identity", () => {
  it("accepts only the latest response identity", () => {
    expect(isLatestRequest(4, 4)).toBe(true);
    expect(isLatestRequest(4, 3)).toBe(false);
  });
});
