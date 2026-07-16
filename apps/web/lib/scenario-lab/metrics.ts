export type MetricCategory = "Service" | "Flow" | "Risk" | "Resources";
export type MetricKey = "slaAttainment" | "averageWaitingTime" | "averageCycleTime" | "p95CycleTime" | "timeWeightedWip" | "timeWeightedQueueLength" | "completionRate" | "terminalFailureRate" | "flowEfficiency" | "totalReworkCount" | "resourceUtilization" | "meanResourceWait" | "probabilityOfImprovement" | "riskProbability";
type Visualization = "value" | "interval" | "probability" | "risk" | "resource";
type MetricPresentation = { key: MetricKey; label: string; unit: string; decimals: number; percentage: boolean; betterDirection: string; emptyState: string; visualization: Visualization; category: MetricCategory };

const metric = (key: MetricKey, label: string, unit: string, category: MetricCategory, betterDirection: string, visualization: Visualization = "interval", percentage = false, decimals = 2): MetricPresentation => ({ key, label, unit, category, betterDirection, visualization, percentage, decimals, emptyState: "Not available" });

export const metricRegistry: Record<MetricKey, MetricPresentation> = {
  slaAttainment: metric("slaAttainment", "SLA attainment", "%", "Service", "Higher attainment", "probability", true, 1),
  averageWaitingTime: metric("averageWaitingTime", "Average waiting time", "min", "Flow", "Lower waiting time"),
  averageCycleTime: metric("averageCycleTime", "Average cycle time", "min", "Service", "Lower cycle time"),
  p95CycleTime: metric("p95CycleTime", "P95 cycle time", "min", "Service", "Lower tail cycle time"),
  timeWeightedWip: metric("timeWeightedWip", "Time-weighted WIP", "tickets", "Flow", "Lower work in progress"),
  timeWeightedQueueLength: metric("timeWeightedQueueLength", "Time-weighted queue length", "tickets", "Flow", "Lower queue length"),
  completionRate: metric("completionRate", "Completion rate", "tickets/min", "Flow", "Higher completion rate", "interval", false, 3),
  terminalFailureRate: metric("terminalFailureRate", "Terminal failure rate", "%", "Risk", "Lower failure rate", "risk", true, 1),
  flowEfficiency: metric("flowEfficiency", "Flow efficiency", "%", "Flow", "Higher flow efficiency", "probability", true, 1),
  totalReworkCount: metric("totalReworkCount", "Rework count", "reworks", "Risk", "Lower rework count"),
  resourceUtilization: metric("resourceUtilization", "Resource utilization", "%", "Resources", "Contextual load", "resource", true, 1),
  meanResourceWait: metric("meanResourceWait", "Mean resource wait", "min", "Resources", "Lower request wait"),
  probabilityOfImprovement: metric("probabilityOfImprovement", "Probability of improvement", "%", "Service", "Direction follows selected metric", "probability", true, 1),
  riskProbability: metric("riskProbability", "Risk probability", "%", "Risk", "Lower threshold violation", "risk", true, 1),
};

export const coreMetricKeys: MetricKey[] = ["slaAttainment", "averageWaitingTime", "averageCycleTime", "p95CycleTime", "timeWeightedWip", "timeWeightedQueueLength", "completionRate", "terminalFailureRate", "flowEfficiency", "totalReworkCount"];

export function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function formatMetric(key: MetricKey, value: unknown): string {
  const definition = metricRegistry[key];
  const number = finiteNumber(value);
  if (number === null) return definition.emptyState;
  const display = definition.percentage ? number * 100 : number;
  const formatted = display.toFixed(definition.decimals);
  return definition.unit ? `${formatted}${definition.unit === "%" ? "%" : ` ${definition.unit}`}` : formatted;
}

export function formatRelative(value: unknown): string {
  const number = finiteNumber(value);
  return number === null ? "Not available" : `${(number * 100).toFixed(1)}%`;
}
