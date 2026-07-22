export type MetricCategory = "Service" | "Flow" | "Risk" | "Resources";
export type MetricKey = "slaAttainment" | "averageWaitingTime" | "averageCycleTime" | "p95CycleTime" | "timeWeightedWip" | "timeWeightedQueueLength" | "completionRate" | "terminalFailureRate" | "flowEfficiency" | "totalReworkCount" | "resourceUtilization" | "meanResourceWait" | "probabilityOfImprovement" | "riskProbability";
type Visualization = "value" | "interval" | "probability" | "risk" | "resource";
type MetricPresentation = { key: MetricKey; label: string; guidedLabel: string; unit: string; decimals: number; percentage: boolean; betterDirection: string; emptyState: string; visualization: Visualization; category: MetricCategory };

const metric = (key: MetricKey, label: string, guidedLabel: string, unit: string, category: MetricCategory, betterDirection: string, visualization: Visualization = "interval", percentage = false, decimals = 2): MetricPresentation => ({ key, label, guidedLabel, unit, category, betterDirection, visualization, percentage, decimals, emptyState: "Not available" });

export const metricRegistry: Record<MetricKey, MetricPresentation> = {
  slaAttainment: metric("slaAttainment", "SLA attainment", "Tickets resolved within the target time", "%", "Service", "Higher attainment", "probability", true, 1),
  averageWaitingTime: metric("averageWaitingTime", "Average waiting time", "Average time tickets waited", "min", "Flow", "Lower waiting time"),
  averageCycleTime: metric("averageCycleTime", "Average cycle time", "Average time to resolve a ticket", "min", "Service", "Lower cycle time"),
  p95CycleTime: metric("p95CycleTime", "P95 cycle time", "Time within which 95% of tickets were resolved", "min", "Service", "Lower tail cycle time"),
  timeWeightedWip: metric("timeWeightedWip", "Time-weighted WIP", "Average tickets in progress over time", "tickets", "Flow", "Lower work in progress"),
  timeWeightedQueueLength: metric("timeWeightedQueueLength", "Time-weighted queue length", "Average number of tickets waiting over time", "tickets", "Flow", "Lower queue length"),
  completionRate: metric("completionRate", "Completion rate", "Tickets completed per minute", "tickets/min", "Flow", "Higher completion rate", "interval", false, 3),
  terminalFailureRate: metric("terminalFailureRate", "Terminal failure rate", "Tickets that ended without completion", "%", "Risk", "Lower failure rate", "risk", true, 1),
  flowEfficiency: metric("flowEfficiency", "Flow efficiency", "Share of time spent processing", "%", "Flow", "Higher flow efficiency", "probability", true, 1),
  totalReworkCount: metric("totalReworkCount", "Rework count", "Tickets needing another pass", "reworks", "Risk", "Lower rework count"),
  resourceUtilization: metric("resourceUtilization", "Resource utilization", "Share of team capacity in use", "%", "Resources", "Contextual load", "resource", true, 1),
  meanResourceWait: metric("meanResourceWait", "Mean resource wait", "Average wait for a team member", "min", "Resources", "Lower request wait"),
  probabilityOfImprovement: metric("probabilityOfImprovement", "Probability of improvement", "How often the change performed better", "%", "Service", "Direction follows selected metric", "probability", true, 1),
  riskProbability: metric("riskProbability", "Risk probability", "Chance of missing a required condition", "%", "Risk", "Lower threshold violation", "risk", true, 1),
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

export function guidedMetricLabel(key: MetricKey, targetMinutes?: number): string {
  const label = metricRegistry[key]?.guidedLabel ?? key;
  return key === "slaAttainment" && typeof targetMinutes === "number" ? `Tickets resolved within ${targetMinutes} minutes` : label;
}

export function formatPercentagePointChange(value: unknown): string {
  const number = finiteNumber(value);
  return number === null ? "Not available" : `${number >= 0 ? "+" : ""}${(number * 100).toFixed(1)} percentage points`;
}
