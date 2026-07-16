export type GuardrailMetric = "slaAttainment" | "averageCycleTime" | "p95CycleTime" | "timeWeightedQueueLength" | "resourcePoolUtilization";
export type GuardrailDraft = { enabled: boolean; metric: GuardrailMetric; value: number; resourcePoolId?: string };

export const guardrailOptions: Record<GuardrailMetric, { label: string; unit: string; operator: "lessThanOrEqual" | "greaterThanOrEqual"; minimum: number; maximum: number; percentage?: boolean }> = {
  slaAttainment: { label: "Minimum SLA attainment", unit: "%", operator: "greaterThanOrEqual", minimum: 0, maximum: 100, percentage: true },
  averageCycleTime: { label: "Maximum average cycle time", unit: "minutes", operator: "lessThanOrEqual", minimum: 0, maximum: 1440 },
  p95CycleTime: { label: "Maximum p95 cycle time", unit: "minutes", operator: "lessThanOrEqual", minimum: 0, maximum: 1440 },
  timeWeightedQueueLength: { label: "Maximum queue length", unit: "tickets", operator: "lessThanOrEqual", minimum: 0, maximum: 10000 },
  resourcePoolUtilization: { label: "Maximum resource utilization", unit: "%", operator: "lessThanOrEqual", minimum: 0, maximum: 100, percentage: true },
};

export function validateGuardrail(draft: GuardrailDraft): string | null {
  if (!draft.enabled) return null;
  const option = guardrailOptions[draft.metric];
  if (!Number.isFinite(draft.value) || draft.value < option.minimum || draft.value > option.maximum) return `Enter a valid threshold between ${option.minimum} and ${option.maximum} ${option.unit}.`;
  if (draft.metric === "resourcePoolUtilization" && !draft.resourcePoolId) return "Choose a resource pool for the utilization guardrail.";
  return null;
}

export function buildGuardrail(draft: GuardrailDraft): Record<string, unknown>[] {
  if (!draft.enabled || validateGuardrail(draft)) return [];
  const option = guardrailOptions[draft.metric];
  return [{
    metric: draft.metric,
    operator: option.operator,
    value: option.percentage ? draft.value / 100 : draft.value,
    ...(draft.metric === "resourcePoolUtilization" ? { resourcePoolId: draft.resourcePoolId } : {}),
  }];
}
