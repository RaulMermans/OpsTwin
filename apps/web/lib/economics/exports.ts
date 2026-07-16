import { asRecord, asRecords } from "../scenario-lab/result-adapter";
import { sanitizeForExport } from "../scenario-lab/exports";

const cell = (value: unknown) => { const text = value === null || value === undefined ? "" : String(value); return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text; };
export function buildEconomicJsonExport(result: unknown): string { return JSON.stringify({ exportVersion: "0.7.0", economicComparison: sanitizeForExport(result) }, null, 2); }
export function buildEconomicCsvExport(resultValue: unknown): string {
  const result = asRecord(resultValue) ?? {};
  const headers = ["scenario_id", "scenario_name", "currency", "baseline_recurring_cost", "scenario_recurring_cost", "recurring_cost_delta", "relative_cost_delta", "probability_lower_cost", "cost_per_completed_item", "objective", "objective_delta", "probability_objective_improved", "tradeoff_classification", "one_time_intervention_cost", "amortized_intervention_cost", "incremental_cost_per_observed_improvement", "economic_guardrail_status", "paired_runs"];
  const rows = asRecords(result.scenarios).map((scenario) => {
    const baseline = asRecord(scenario.baselineCost); const current = asRecord(scenario.scenarioCost); const delta = asRecord(scenario.recurringCostDelta); const intervention = asRecord(scenario.intervention); const guardrails = asRecords(scenario.economicGuardrails);
    return [scenario.scenarioId, scenario.scenarioName, result.currency, asRecord(baseline?.recurringOperatingCost)?.mean, asRecord(current?.recurringOperatingCost)?.mean, asRecord(delta?.absoluteDelta)?.mean, asRecord(delta?.relativeDelta)?.mean, scenario.probabilityLowerCost, asRecord(current?.costPerCompletedItem)?.mean, scenario.objectiveMetric, scenario.objectiveMeanPairedDelta, scenario.probabilityOperationallyImproved, scenario.tradeoffClassification, intervention?.oneTimeCost, intervention?.amortizedCostPerPeriod, scenario.incrementalCostPerObservedImprovement, guardrails.every((item) => item.passed === true) ? "passed" : guardrails.length ? "failed_or_unavailable" : "not_configured", scenario.pairedRunCount].map(cell).join(",");
  });
  return [headers.join(","), ...rows].join("\n");
}
