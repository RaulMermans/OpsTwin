import type { WorkflowOperationalModel } from "./presentation-model";

type Override = { entityType: string; entityId: string; field: string; operation: string; value: unknown };
type Scenario = { id: string; name: string; overrides: Override[] };
export type WorkflowChange = { id: string; entityId: string; targetKind: "source" | "stage" | "resource" | "route" | "sla"; field: string; baselineValue: unknown; scenarioValue: unknown; direction: "increase" | "decrease" | "changed" | "unchanged"; targetIds: string[] };

function valueAt(model: WorkflowOperationalModel, override: Override): unknown {
  if (override.entityType === "resourcePool") return model.resourcePools.find((item) => item.id === override.entityId)?.capacity;
  if (override.entityType === "source") {
    const source = model.sources.find((item) => item.id === override.entityId);
    if (override.field === "arrivalInterval") return source?.arrival?.interval;
    if (override.field === "meanInterarrivalTime") return source?.arrival?.meanInterarrivalTime;
    return undefined;
  }
  if (override.entityType === "stage") {
    const stage = model.stages.find((item) => item.id === override.entityId);
    if (override.field === "failure.probability") return stage?.failure?.probability;
    if (override.field === "maximumReworkAttempts") return stage?.failure?.maximumReworkAttempts;
    const processingKey = override.field.match(/^processing\.(?:fixed|exponential|uniform|triangular)\.(value|mean|minimum|mode|maximum)$/)?.[1];
    if (processingKey) return stage?.processingTime?.[processingKey];
    return undefined;
  }
  if (override.entityType === "route") {
    const [routeId, targetId] = override.entityId.split(":", 2);
    const route = model.routes.find((item) => item.id === routeId);
    const index = route?.options.findIndex((option) => (option.targetId ?? "completion") === targetId) ?? -1;
    return route?.options[index]?.probability;
  }
  if (override.entityType === "slaRule") return model.slaRules?.find((item) => item.id === override.entityId)?.targetDuration;
  return undefined;
}

function kindFor(entityType: string): WorkflowChange["targetKind"] | null {
  if (entityType === "resourcePool") return "resource";
  if (entityType === "source" || entityType === "stage" || entityType === "route") return entityType;
  if (entityType === "slaRule") return "sla";
  return null;
}

function exists(model: WorkflowOperationalModel, kind: WorkflowChange["targetKind"], id: string) {
  if (kind === "resource") return model.resourcePools.filter((item) => item.id === id).length === 1;
  if (kind === "source") return model.sources.filter((item) => item.id === id).length === 1;
  if (kind === "stage") return model.stages.filter((item) => item.id === id).length === 1;
  if (kind === "route") {
    const [routeId, targetId] = id.split(":", 2);
    const routes = model.routes.filter((item) => item.id === routeId);
    return routes.length === 1 && routes[0].options.filter((option) => (option.targetId ?? "completion") === targetId).length === 1;
  }
  return (model.slaRules?.filter((item) => item.id === id).length ?? 0) === 1;
}

function direction(baseline: unknown, scenario: unknown): WorkflowChange["direction"] {
  if (typeof baseline === "number" && typeof scenario === "number") return scenario > baseline ? "increase" : scenario < baseline ? "decrease" : "unchanged";
  return Object.is(baseline, scenario) ? "unchanged" : "changed";
}

export function mapScenarioChanges(model: WorkflowOperationalModel, scenario: Scenario | null | undefined): { changes: WorkflowChange[]; warnings: string[] } {
  if (!scenario) return { changes: [], warnings: [] };
  const changes: WorkflowChange[] = []; const warnings: string[] = [];
  scenario.overrides.forEach((override, index) => {
    const kind = kindFor(override.entityType);
    if (!kind || !exists(model, kind, override.entityId)) {
      warnings.push(`Scenario override references unknown ${kind ?? override.entityType} ${override.entityId}.`);
      return;
    }
    const baselineValue = valueAt(model, override);
    let targetIds = [override.entityId];
    if (kind === "route") {
      const [routeId, targetId] = override.entityId.split(":", 2);
      const route = model.routes.find((item) => item.id === routeId)!;
      const optionIndex = route.options.findIndex((option) => (option.targetId ?? "completion") === targetId);
      targetIds = [`route:${routeId}:${optionIndex}`];
    }
    changes.push({ id: `change:${scenario.id}:${index}`, entityId: override.entityId, targetKind: kind, field: override.field, baselineValue, scenarioValue: override.value, direction: direction(baselineValue, override.value), targetIds });
  });
  return { changes, warnings };
}
