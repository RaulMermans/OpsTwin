import { asRecord, asRecords, getScenarioStatus, guardrailCopy, rankingFor } from "./result-adapter";

const unsafeKeys = /^(events?|returnedEvents|eventLog|stack|stackTrace|password|secret|token|apiKey|path|privatePath|filesystemPath|browserState)$/i;

export function sanitizeForExport(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sanitizeForExport);
  const object = asRecord(value);
  if (!object) return value;
  return Object.fromEntries(Object.entries(object).filter(([key]) => !unsafeKeys.test(key)).map(([key, child]) => [key, sanitizeForExport(child)]));
}

export function buildJsonExport(input: { baseline: unknown; scenarios: unknown; settings: unknown; result: unknown; timestamp?: string }): string {
  const result = asRecord(input.result);
  return JSON.stringify({
    exportVersion: "1.0.0",
    exportedAt: input.timestamp ?? new Date().toISOString(),
    baselineDisplayAssumptions: sanitizeForExport(input.baseline),
    scenarioDefinitions: sanitizeForExport(input.scenarios),
    executionSettings: sanitizeForExport(input.settings),
    comparisonResult: sanitizeForExport(input.result),
    integrityMetadata: sanitizeForExport(result?.integrity ?? null),
  }, null, 2);
}

const cell = (value: unknown): string => {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

export function buildCsvExport(resultValue: unknown): string {
  const result = asRecord(resultValue) ?? {};
  const objective = String(asRecord(result.objective)?.metric ?? "");
  const headers = ["scenario_id", "scenario_name", "status", "rank", "objective", "objective_mean_delta", "relative_delta", "probability_improved", "probability_degraded", "guardrail_status", "paired_runs", "baseline_risk", "scenario_risk"];
  const rows = asRecords(result.scenarios).map((scenario) => {
    const ranking = rankingFor(result, String(scenario.scenarioId ?? ""));
    const paired = asRecord(asRecord(scenario.pairedMetrics)?.[objective]);
    const improvement = asRecord(paired?.improvement);
    const risk = asRecords(scenario.riskComparisons)[0];
    return [scenario.scenarioId, scenario.scenarioName, getScenarioStatus(scenario, ranking), ranking?.rank, objective, asRecord(paired?.absoluteDelta)?.mean, asRecord(paired?.relativeDelta)?.mean, improvement?.probabilityOfImprovement, improvement?.probabilityOfDegradation, guardrailCopy(scenario), scenario.pairedRunCount, risk?.baselineProbability, risk?.scenarioProbability].map(cell).join(",");
  });
  return [headers.join(","), ...rows].join("\n");
}

export function downloadText(filename: string, content: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
