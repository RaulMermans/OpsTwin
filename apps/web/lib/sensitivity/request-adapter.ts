import type { BaselineModel } from "../templates/support";

export type SensitivityTargetKey = "level1Capacity" | "level2Capacity" | "arrivalMean" | "triageMean" | "qualityDuration" | "reworkProbability" | "reworkAttempts" | "slaTarget";
export type SensitivityMetric = "averageCycleTime" | "p95CycleTime" | "slaAttainment" | "timeWeightedQueueLength";
export type SensitivityDraft = { targetKey: SensitivityTargetKey; values: number[]; runs: 10 | 25 | 50 | 100; metric: SensitivityMetric };

export const sensitivityTargets: Record<SensitivityTargetKey, { category: string; entity: string; fieldLabel: string; entityType: string; entityId: string; field: string }> = {
  level1Capacity: { category: "Resource pool", entity: "Level 1 agents", fieldLabel: "Capacity", entityType: "resourcePool", entityId: "level-1-agents", field: "capacity" },
  level2Capacity: { category: "Resource pool", entity: "Level 2 agents", fieldLabel: "Capacity", entityType: "resourcePool", entityId: "level-2-agents", field: "capacity" },
  arrivalMean: { category: "Demand", entity: "Incoming tickets", fieldLabel: "Mean interarrival time", entityType: "source", entityId: "incoming-tickets", field: "meanInterarrivalTime" },
  triageMean: { category: "Processing", entity: "Triage", fieldLabel: "Exponential mean", entityType: "stage", entityId: "triage", field: "processing.exponential.mean" },
  qualityDuration: { category: "Processing", entity: "Quality check", fieldLabel: "Fixed duration", entityType: "stage", entityId: "quality-check", field: "processing.fixed.value" },
  reworkProbability: { category: "Failure and rework", entity: "Quality check", fieldLabel: "Failure probability", entityType: "stage", entityId: "quality-check", field: "failure.probability" },
  reworkAttempts: { category: "Failure and rework", entity: "Quality check", fieldLabel: "Maximum rework attempts", entityType: "stage", entityId: "quality-check", field: "maximumReworkAttempts" },
  slaTarget: { category: "SLA", entity: "Support resolution", fieldLabel: "Target duration", entityType: "slaRule", entityId: "support-resolution-sla", field: "targetDuration" },
};

export function parseSensitivityValues(text: string): { values: number[]; error: string | null } {
  const parts = text.split(",").map((value) => value.trim()).filter(Boolean);
  const values = parts.map(Number);
  if (values.some((value) => !Number.isFinite(value))) return { values: [], error: "Tested values must be numbers separated by commas." };
  if (values.length < 2 || values.length > 6) return { values: [], error: "Enter between 2 and 6 tested values." };
  if (new Set(values).size !== values.length) return { values: [], error: "Tested values must be distinct." };
  return { values, error: null };
}

export function buildSensitivityRequest(model: BaselineModel, draft: SensitivityDraft) {
  const target = sensitivityTargets[draft.targetKey];
  return {
    schemaVersion: "0.6.0",
    baselineModel: model,
    target: { entityType: target.entityType, entityId: target.entityId, field: target.field },
    values: draft.values,
    execution: { baseSeed: 20260716, runCount: draft.runs, confidenceLevel: 0.95, minimumSuccessfulRunRatio: 1, minimumPairedRunRatio: 1, observation: { warmupDuration: 0 } },
    metrics: [draft.metric],
    thresholds: {},
  };
}
