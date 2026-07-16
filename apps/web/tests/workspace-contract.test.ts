import { describe, expect, it } from "vitest";

import { buildBaseline, DEFAULT_FORM } from "../lib/templates/support";
import { buildScenario, estimateWork, validateScenarios } from "../lib/scenarios/builders";
import { isComparisonResult, parseApiError } from "../lib/api/simulation";

describe("support product mapping", () => {
  it("maps the eight canonical defaults without mutating the source", () => {
    const edited = { ...DEFAULT_FORM, level1Capacity: 5 };
    const model = buildBaseline(edited);
    expect(DEFAULT_FORM.level1Capacity).toBe(4);
    expect(model.resourcePools.find((pool) => pool.id === "level-1-agents")?.capacity).toBe(5);
    expect(model.sources[0].arrival.meanInterarrivalTime).toBe(1.5);
  });

  it("maps four guided scenario targets and guards work", () => {
    expect(buildScenario({ id: "a", name: "Demand", type: "demand", value: 20 }, DEFAULT_FORM).overrides[0]).toMatchObject({ entityId: "incoming-tickets", field: "arrival.poisson.meanInterarrivalTime", operation: "replace" });
    expect(buildScenario({ id: "b", name: "Staffing", type: "level1Staffing", value: 1 }, DEFAULT_FORM).overrides[0].value).toBe(5);
    expect(buildScenario({ id: "c", name: "Process", type: "triageProcess", value: 25 }, DEFAULT_FORM).overrides[0].value).toBe(1.5);
    expect(buildScenario({ id: "d", name: "Quality", type: "quality", value: 50 }, DEFAULT_FORM).overrides[0].value).toBe(0.05);
    expect(estimateWork(100, 50, 2)).toBe(15000);
    expect(validateScenarios([{ id: "a", name: "A", type: "demand", value: 10 }, { id: "a", name: "B", type: "demand", value: 20 }])).toMatch(/IDs must be unique/i);
  });
});

describe("public response boundary", () => {
  it("rejects unknown result JSON and parses stable errors", () => {
    expect(isComparisonResult({ schemaVersion: "0.5.0" })).toBe(false);
    expect(parseApiError({ error: { code: "WORK_BUDGET_EXCEEDED", message: "Too much work", fieldErrors: [], details: {} } }).code).toBe("WORK_BUDGET_EXCEEDED");
    expect(parseApiError({ stack: "private" }).code).toBe("UNEXPECTED_RESPONSE");
  });
});
