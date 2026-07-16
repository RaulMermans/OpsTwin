import { describe, expect, it } from "vitest";

import { buildWorkflowPresentation } from "../lib/workflow/presentation-model";
import { normalizeOverlayValues } from "../lib/workflow/overlays";
import { mapScenarioChanges } from "../lib/workflow/scenario-changes";
import { buildScenario } from "../lib/scenarios/builders";
import { buildBaseline, DEFAULT_FORM } from "../lib/templates/support";

describe("workflow presentation mapping", () => {
  it("maps the canonical source and entry destination", () => {
    const view = buildWorkflowPresentation(buildBaseline({ ...DEFAULT_FORM }));
    expect(view.nodes.find((node) => node.id === "incoming-tickets")).toMatchObject({ kind: "source", row: 0, column: 2 });
    expect(view.edges).toContainEqual(expect.objectContaining({ id: "entry:incoming-tickets:triage", fromId: "incoming-tickets", toId: "triage" }));
  });

  it("maps every canonical stage in stable order", () => {
    const view = buildWorkflowPresentation(buildBaseline({ ...DEFAULT_FORM }));
    expect(view.nodes.filter((node) => node.kind === "stage").map((node) => node.id)).toEqual(["triage", "level-1", "level-2", "quality-check"]);
  });

  it("maps resource relationships", () => {
    const view = buildWorkflowPresentation(buildBaseline({ ...DEFAULT_FORM }));
    expect(view.resourceLinks).toContainEqual({ id: "resource:level-1-agents:level-1", resourceId: "level-1-agents", stageId: "level-1" });
    expect(view.nodes.find((node) => node.id === "quality-team")).toMatchObject({ kind: "resource" });
  });

  it("maps route probabilities and rework", () => {
    const view = buildWorkflowPresentation(buildBaseline({ ...DEFAULT_FORM }));
    expect(view.edges).toContainEqual(expect.objectContaining({ routeId: "triage-routing", probability: 0.8, rework: false }));
    expect(view.edges).toContainEqual(expect.objectContaining({ routeId: "quality-rework", fromId: "quality-check", toId: "level-2", rework: true }));
  });

  it("maps a stable completion terminal", () => {
    const view = buildWorkflowPresentation(buildBaseline({ ...DEFAULT_FORM }));
    expect(view.nodes.find((node) => node.id === "terminal:quality-resolved:0")).toMatchObject({ kind: "terminal", label: "Completed" });
  });

  it("does not mutate baseline input", () => {
    const model = buildBaseline({ ...DEFAULT_FORM });
    const before = structuredClone(model);
    buildWorkflowPresentation(model);
    expect(model).toEqual(before);
  });

  it("is deterministic across calls", () => {
    const model = buildBaseline({ ...DEFAULT_FORM });
    expect(buildWorkflowPresentation(model)).toEqual(buildWorkflowPresentation(model));
  });

  it("reports unknown references without throwing", () => {
    const model = structuredClone(buildBaseline({ ...DEFAULT_FORM }));
    (model.routes[0].options[0] as { targetId?: string }).targetId = "missing-stage";
    const view = buildWorkflowPresentation(model);
    expect(view.valid).toBe(false);
    expect(view.warnings).toContain("Route triage-routing references unknown stage missing-stage.");
    expect(view.edges.some((edge) => edge.toId === "missing-stage")).toBe(false);
  });

  it("rejects duplicate visual IDs", () => {
    const model = structuredClone(buildBaseline({ ...DEFAULT_FORM }));
    model.routes[1].id = model.routes[0].id;
    const view = buildWorkflowPresentation(model);
    expect(view.valid).toBe(false);
    expect(view.warnings).toContain("Duplicate visual ID route:triage-routing:0.");
  });
});

describe("scenario change mapping", () => {
  const model = buildBaseline({ ...DEFAULT_FORM });

  it.each([
    ["level1Staffing", "level-1-agents", "resource"],
    ["triageProcess", "triage", "stage"],
    ["demand", "incoming-tickets", "source"],
    ["quality", "quality-check", "stage"],
  ] as const)("maps %s to %s", (type, id, targetKind) => {
    const scenario = buildScenario({ id: "scenario-x", name: "Controlled change", type, value: 10 }, DEFAULT_FORM);
    expect(mapScenarioChanges(model, scenario).changes[0]).toMatchObject({ entityId: id, targetKind });
  });

  it("maps route and SLA overrides explicitly", () => {
    const mapped = mapScenarioChanges(model, { id: "x", name: "x", overrides: [
      { entityType: "route", entityId: "triage-routing", field: "options.0.probability", operation: "replace", value: 0.7 },
      { entityType: "slaRule", entityId: "support-resolution-sla", field: "targetDuration", operation: "replace", value: 45 },
    ] });
    expect(mapped.changes.map((change) => change.targetKind)).toEqual(["route", "sla"]);
  });

  it("warns for an unknown target and leaves known entities unchanged", () => {
    const mapped = mapScenarioChanges(model, { id: "x", name: "x", overrides: [{ entityType: "stage", entityId: "missing", field: "processing.fixed.value", operation: "replace", value: 1 }] });
    expect(mapped.changes).toHaveLength(0);
    expect(mapped.warnings).toEqual(["Scenario override references unknown stage missing."]);
  });
});

describe("workflow overlay scaling", () => {
  it("maps finite minimum and maximum exactly", () => expect(normalizeOverlayValues({ a: 4, b: 8 })).toEqual({ a: 0, b: 1 }));
  it("maps equal finite values to neutral intensity", () => expect(normalizeOverlayValues({ a: 4, b: 4 })).toEqual({ a: 0.5, b: 0.5 }));
  it("preserves missing and non-finite values as unavailable", () => expect(normalizeOverlayValues({ a: null, b: Number.NaN, c: Number.POSITIVE_INFINITY })).toEqual({ a: null, b: null, c: null }));
  it("scales only across visible finite values", () => expect(normalizeOverlayValues({ a: -2, b: 0, c: 2, d: null })).toEqual({ a: 0, b: 0.5, c: 1, d: null }));
});
