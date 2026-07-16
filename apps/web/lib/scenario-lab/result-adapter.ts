import { finiteNumber, type MetricKey } from "./metrics";

export type UnknownRecord = Record<string, unknown>;
export const asRecord = (value: unknown): UnknownRecord | null => typeof value === "object" && value !== null && !Array.isArray(value) ? value as UnknownRecord : null;
export const asRecords = (value: unknown): UnknownRecord[] => Array.isArray(value) ? value.map(asRecord).filter((item): item is UnknownRecord => item !== null) : [];

export function rankingFor(result: Record<string, unknown>, scenarioId: string): UnknownRecord | null {
  return asRecords(result.ranking).find((item) => item.scenarioId === scenarioId) ?? null;
}

export function getScenarioStatus(scenarioValue: unknown, rankingValue: unknown): string {
  const scenario = asRecord(scenarioValue);
  const ranking = asRecord(rankingValue);
  if (!scenario) return "Result unavailable";
  if (scenario.status === "failed") {
    const category = asRecord(scenario.failure)?.category;
    if (category === "override_validation" || category === "materialization_validation" || category === "domain_validation") return "Invalid scenario";
    if (category === "paired_ratio_failure") return "Insufficient paired runs";
    if (category === "paired_execution" || category === "serialization_failure") return "Execution failed";
    return "Execution failed";
  }
  if (scenario.status !== "valid") return "Result unavailable";
  if (ranking && finiteNumber(ranking.rank) !== null) return "Ranked";
  if (scenario.eligible === true) return "Eligible but unranked";
  if (asRecords(scenario.guardrails).some((guardrail) => guardrail.passed === false)) return "Ineligible - guardrail failed";
  const requested = finiteNumber(scenario.requestedRunCount);
  const successful = finiteNumber(scenario.scenarioSuccessfulRunCount);
  const paired = finiteNumber(scenario.pairedRunCount);
  if (requested !== null && successful !== null && successful < requested) return "Insufficient valid runs";
  if (requested !== null && paired !== null && paired < requested) return "Insufficient paired runs";
  return "Completed without ranking";
}

export function aggregateMean(container: unknown, metric: string): number | null {
  return finiteNumber(asRecord(asRecord(container)?.[metric])?.mean);
}

export function pairedMetric(scenario: UnknownRecord, key: MetricKey): UnknownRecord | null {
  return asRecord(asRecord(scenario.pairedMetrics)?.[key]);
}

export function confidence(metricValue: UnknownRecord | null): UnknownRecord | null {
  return asRecord(asRecord(metricValue?.absoluteDelta)?.confidenceInterval);
}

export function guardrailCopy(scenario: UnknownRecord): string {
  const guardrails = asRecords(scenario.guardrails);
  if (!guardrails.length) return "No guardrails configured";
  return guardrails.every((item) => item.passed === true) ? "Passed the configured guardrail" : "Failed the configured guardrail";
}
