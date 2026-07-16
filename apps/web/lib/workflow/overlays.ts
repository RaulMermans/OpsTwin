import { asRecord, asRecords } from "../scenario-lab/result-adapter";
export { normalizeOverlayValues } from "./display-scaling";

export type StageOverlayMetric = "averageWaitingTime" | "timeWeightedQueueLength" | "failureRate" | "reworkCount" | "visitCount";
export type ResourceOverlayMetric = "utilization" | "idleCapacityProportion" | "meanRequestWait" | "maximumConcurrentUsage";
export type WorkflowOverlayMetric = StageOverlayMetric | ResourceOverlayMetric;

export const overlayOptions: { id: WorkflowOverlayMetric; label: string; kind: "stage" | "resource" }[] = [
  { id: "averageWaitingTime", label: "Observed waiting", kind: "stage" },
  { id: "timeWeightedQueueLength", label: "Observed queue", kind: "stage" },
  { id: "failureRate", label: "Observed failure", kind: "stage" },
  { id: "reworkCount", label: "Observed rework", kind: "stage" },
  { id: "visitCount", label: "Observed visits", kind: "stage" },
  { id: "utilization", label: "Observed utilization", kind: "resource" },
  { id: "idleCapacityProportion", label: "Observed idle proportion", kind: "resource" },
  { id: "meanRequestWait", label: "Observed request wait", kind: "resource" },
  { id: "maximumConcurrentUsage", label: "Observed concurrent usage", kind: "resource" },
];

function mean(value: unknown): number | null {
  const candidate = asRecord(value)?.mean;
  return typeof candidate === "number" && Number.isFinite(candidate) ? candidate : null;
}

export function workflowOverlayValues(result: unknown, scenarioId: string | null, metric: WorkflowOverlayMetric): Record<string, number | null> {
  const root = asRecord(result); if (!root) return {};
  const scenario = scenarioId ? asRecords(root.scenarios).find((item) => item.scenarioId === scenarioId) : null;
  const container = scenario?.status === "valid" ? asRecord(scenario.variant) : asRecord(root.baseline);
  const option = overlayOptions.find((item) => item.id === metric)!;
  const group = option.kind === "stage" ? asRecords(container?.stageMetrics) : asRecords(container?.resourcePoolMetrics);
  const idKey = option.kind === "stage" ? "stageId" : "resourcePoolId";
  return Object.fromEntries(group.map((item) => [String(item[idKey]), mean(asRecord(item.metrics)?.[metric])]));
}
