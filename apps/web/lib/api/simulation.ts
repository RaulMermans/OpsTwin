type RecordValue = Record<string, unknown>;
export type ApiError = { code: string; message: string; fieldErrors: unknown[]; details: RecordValue };
export type ComparisonResult = RecordValue & { schemaVersion: "0.5.0"; baselineModelHash: string; requestedRunCount: number; baseline: RecordValue; scenarios: RecordValue[]; ranking: RecordValue[]; objective: RecordValue; workBudget: RecordValue; execution: RecordValue; integrity: { status: "passed"; checksRun: number } };
export type SensitivityPoint = { parameterValue: number; isBaselineValue: boolean; status: "valid" | "failed"; mean: number | null; confidenceIntervalLower: number | null; confidenceIntervalUpper: number | null; observedElasticity: number | null };
export type SensitivityCurve = { metric: string; unit: string; direction: string; points: SensitivityPoint[]; finiteDifferences: RecordValue[]; monotonicity: string; thresholdCrossings: RecordValue[] };
export type SensitivityResult = RecordValue & { schemaVersion: "0.6.0"; baselineModelHash: string; target: RecordValue; originalValues: number[]; canonicalValues: number[]; requestedRunCount: number; baseSeed: number; seedScheduleAlgorithm: "sha256_first_64_bits"; runSeeds: RecordValue[]; confidenceLevel: number; responseCurves: SensitivityCurve[]; values: RecordValue[]; workBudget: RecordValue; execution: RecordValue; integrity: { status: "passed"; checksRun: number } };
export type EconomicComparisonResult = RecordValue & { schemaVersion: "0.7.0"; currency: string; modelTimeUnit: string; operationalComparison: ComparisonResult; baselineCost: RecordValue; scenarios: RecordValue[]; workBudget: RecordValue; execution: { economicSnapshotEvaluations: number; ordinaryRunRetainedEventCount: 0 }; integrity: { status: "passed"; checksRun: number } };
const isRecord = (value: unknown): value is RecordValue => typeof value === "object" && value !== null && !Array.isArray(value);
const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const isNullableFinite = (value: unknown): value is number | null => value === null || isFiniteNumber(value);
const isSensitivityPoint = (value: unknown): value is SensitivityPoint => isRecord(value) && isFiniteNumber(value.parameterValue) && typeof value.isBaselineValue === "boolean" && (value.status === "valid" || value.status === "failed") && isNullableFinite(value.mean) && isNullableFinite(value.confidenceIntervalLower) && isNullableFinite(value.confidenceIntervalUpper) && isNullableFinite(value.observedElasticity);
const isSensitivityCurve = (value: unknown): value is SensitivityCurve => isRecord(value) && typeof value.metric === "string" && typeof value.unit === "string" && typeof value.direction === "string" && Array.isArray(value.points) && value.points.every(isSensitivityPoint) && Array.isArray(value.finiteDifferences) && typeof value.monotonicity === "string" && Array.isArray(value.thresholdCrossings);

export function isComparisonResult(value: unknown): value is ComparisonResult {
  if (!isRecord(value)) return false;
  return value.schemaVersion === "0.5.0" && typeof value.baselineModelHash === "string" && typeof value.requestedRunCount === "number" && isRecord(value.baseline) && Array.isArray(value.scenarios) && Array.isArray(value.ranking) && isRecord(value.objective) && isRecord(value.workBudget) && isRecord(value.execution) && isRecord(value.integrity) && value.integrity.status === "passed";
}
export function isSensitivityResult(value: unknown): value is SensitivityResult {
  if (!isRecord(value)) return false;
  return value.schemaVersion === "0.6.0" && typeof value.baselineModelHash === "string" && /^[0-9a-f]{64}$/.test(value.baselineModelHash) && isRecord(value.target) && Array.isArray(value.originalValues) && value.originalValues.every(isFiniteNumber) && Array.isArray(value.canonicalValues) && value.canonicalValues.every(isFiniteNumber) && Number.isInteger(value.requestedRunCount) && isFiniteNumber(value.baseSeed) && value.seedScheduleAlgorithm === "sha256_first_64_bits" && Array.isArray(value.runSeeds) && isFiniteNumber(value.confidenceLevel) && Array.isArray(value.responseCurves) && value.responseCurves.length > 0 && value.responseCurves.every(isSensitivityCurve) && Array.isArray(value.values) && isRecord(value.workBudget) && isRecord(value.execution) && isRecord(value.integrity) && value.integrity.status === "passed" && Number.isInteger(value.integrity.checksRun);
}
export function isEconomicComparisonResult(value: unknown): value is EconomicComparisonResult {
  if (!isRecord(value)) return false;
  return value.schemaVersion === "0.7.0" && typeof value.currency === "string" && /^[A-Z]{3}$/.test(value.currency) && typeof value.modelTimeUnit === "string" && isComparisonResult(value.operationalComparison) && isRecord(value.baselineCost) && Array.isArray(value.scenarios) && isRecord(value.workBudget) && isRecord(value.execution) && Number.isInteger(value.execution.economicSnapshotEvaluations) && value.execution.ordinaryRunRetainedEventCount === 0 && isRecord(value.integrity) && value.integrity.status === "passed" && Number.isInteger(value.integrity.checksRun);
}
export function parseApiError(value: unknown): ApiError {
  if (isRecord(value) && isRecord(value.error) && typeof value.error.code === "string" && typeof value.error.message === "string") return { code: value.error.code, message: value.error.message, fieldErrors: Array.isArray(value.error.fieldErrors) ? value.error.fieldErrors : [], details: isRecord(value.error.details) ? value.error.details : {} };
  return { code: "UNEXPECTED_RESPONSE", message: "The simulation service returned an unexpected response.", fieldErrors: [], details: {} };
}
async function request(path: string, init: RequestInit, signal?: AbortSignal): Promise<unknown> {
  const timeout = new AbortController(); let timedOut = false; const timer = window.setTimeout(() => { timedOut = true; timeout.abort(); }, 60_000); const abort = () => timeout.abort();
  signal?.addEventListener("abort", abort, { once: true });
  try {
    const response = await fetch(path, { ...init, signal: timeout.signal, headers: { "content-type": "application/json", ...init.headers } });
    let body: unknown;
    try { body = await response.json(); } catch { throw { code: "UNEXPECTED_RESPONSE", message: "The simulation service returned an unexpected response.", fieldErrors: [], details: {} } satisfies ApiError; }
    if (!response.ok) throw parseApiError(body); return body;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw {
      code: signal?.aborted && !timedOut ? "CANCELLED" : "TIMEOUT",
      message: signal?.aborted && !timedOut ? "The browser stopped waiting for this comparison. The server may still finish processing the request." : "The comparison took longer than the browser waiting limit. Your inputs have been preserved.",
      fieldErrors: [], details: {},
    } satisfies ApiError;
    if (isRecord(error) && typeof error.code === "string" && typeof error.message === "string") throw error;
    if (error instanceof TypeError) throw { code: "NETWORK_ERROR", message: "The simulation service could not be reached. Your inputs have been preserved.", fieldErrors: [], details: {} } satisfies ApiError;
    throw error;
  } finally { window.clearTimeout(timer); signal?.removeEventListener("abort", abort); }
}
export async function checkSimulationHealth(): Promise<boolean> { const result = await request("/api/simulation/health", { method: "GET" }); return isRecord(result) && result.status === "ok"; }
export async function runScenarioComparison(payload: unknown, signal?: AbortSignal): Promise<ComparisonResult> { const result = await request("/api/simulation/compare/scenarios", { method: "POST", body: JSON.stringify(payload) }, signal); if (!isComparisonResult(result)) throw parseApiError(result); return result; }
export async function runSensitivityAnalysis(payload: unknown, signal?: AbortSignal): Promise<SensitivityResult> { const result = await request("/api/simulation/analyze/sensitivity", { method: "POST", body: JSON.stringify(payload) }, signal); if (!isSensitivityResult(result)) throw parseApiError(result); return result; }
export async function runEconomicComparison(payload: unknown, signal?: AbortSignal): Promise<EconomicComparisonResult> { const result = await request("/api/simulation/analyze/economics", { method: "POST", body: JSON.stringify(payload) }, signal); if (!isEconomicComparisonResult(result)) throw parseApiError(result); return result; }
