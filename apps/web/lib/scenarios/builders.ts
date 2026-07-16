import type { BaselineForm } from "../templates/support";

export type ScenarioType = "demand" | "level1Staffing" | "level2Staffing" | "triageProcess" | "quality";
export type ScenarioDraft = { id: string; name: string; type: ScenarioType; value: number };
type Override = { entityType: string; entityId: string; field: string; operation: "replace"; value: number };

export function buildScenario(draft: ScenarioDraft, baseline: BaselineForm): { id: string; name: string; overrides: Override[] } {
  let override: Override;
  if (draft.type === "demand") override = { entityType: "source", entityId: "incoming-tickets", field: "arrival.poisson.meanInterarrivalTime", operation: "replace", value: baseline.arrivalInterval / (1 + draft.value / 100) };
  else if (draft.type === "level1Staffing" || draft.type === "level2Staffing") {
    const level1 = draft.type === "level1Staffing";
    override = { entityType: "resourcePool", entityId: level1 ? "level-1-agents" : "level-2-agents", field: "capacity", operation: "replace", value: (level1 ? baseline.level1Capacity : baseline.level2Capacity) + draft.value };
  } else if (draft.type === "triageProcess") override = { entityType: "stage", entityId: "triage", field: "processing.exponential.mean", operation: "replace", value: baseline.triageDuration * (1 - draft.value / 100) };
  else override = { entityType: "stage", entityId: "quality-check", field: "failure.probability", operation: "replace", value: (baseline.reworkProbability / 100) * (1 - draft.value / 100) };
  return { id: draft.id, name: draft.name, overrides: [{ ...override, value: Number(override.value.toFixed(6)) }] };
}

export const estimateWork = (items: number, runs: number, scenarioCount: number) => items * runs * (scenarioCount + 1);
export function validateScenarios(scenarios: ScenarioDraft[]): string | null {
  if (scenarios.length === 0) return "Add at least one scenario before running the comparison.";
  if (scenarios.length > 3) return "Use no more than three scenarios.";
  if (new Set(scenarios.map((item) => item.id)).size !== scenarios.length) return "Scenario IDs must be unique.";
  if (scenarios.some((item) => !item.name.trim() || !Number.isFinite(item.value) || item.value <= 0)) return "Each scenario needs a name and a positive change.";
  return null;
}
