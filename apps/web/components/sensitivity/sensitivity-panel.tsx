"use client";

import { useMemo, useState } from "react";

import { runSensitivityAnalysis, type ApiError, type SensitivityCurve, type SensitivityResult } from "../../lib/api/simulation";
import { buildSensitivityRequest, parseSensitivityValues, sensitivityTargets, type SensitivityMetric, type SensitivityTargetKey } from "../../lib/sensitivity/request-adapter";
import { buildBaseline, type BaselineForm } from "../../lib/templates/support";

const metricLabels: Record<SensitivityMetric, string> = { averageCycleTime: "Average cycle time", p95CycleTime: "P95 cycle time", slaAttainment: "SLA attainment", timeWeightedQueueLength: "Time-weighted queue length" };
const targetEntries = Object.entries(sensitivityTargets) as [SensitivityTargetKey, (typeof sensitivityTargets)[SensitivityTargetKey]][];

export function SensitivityPanel({ baseline, health, guided = false }: { baseline: BaselineForm; health: "checking" | "ready" | "unavailable"; guided?: boolean }) {
  const [targetKey, setTargetKey] = useState<SensitivityTargetKey>("level1Capacity");
  const [valueText, setValueText] = useState("2, 3, 4, 5");
  const [runs, setRuns] = useState<10 | 25 | 50 | 100>(50);
  const [metric, setMetric] = useState<SensitivityMetric>("averageCycleTime");
  const [state, setState] = useState<"idle" | "running">("idle");
  const [result, setResult] = useState<SensitivityResult | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const parsed = parseSensitivityValues(valueText);
  const category = sensitivityTargets[targetKey].category;
  const categoryTargets = targetEntries.filter(([, target]) => target.category === category);
  const work = 100 * runs * (parsed.values.length || 0);
  const baselineValue = targetKey === "level1Capacity" ? baseline.level1Capacity : targetKey === "level2Capacity" ? baseline.level2Capacity : targetKey === "arrivalMean" ? baseline.arrivalInterval : targetKey === "triageMean" ? baseline.triageDuration : targetKey === "qualityDuration" ? baseline.qualityDuration : targetKey === "reworkProbability" ? baseline.reworkProbability / 100 : targetKey === "slaTarget" ? baseline.slaTarget : 2;
  const baselineMissing = !parsed.error && !parsed.values.includes(baselineValue);

  async function submit() {
    if (parsed.error || baselineMissing || state === "running") return;
    setState("running"); setResult(null); setError(null);
    try {
      setResult(await runSensitivityAnalysis(buildSensitivityRequest(buildBaseline(baseline), { targetKey, values: parsed.values, runs, metric })));
    } catch (caught) {
      setError(caught as ApiError);
    } finally { setState("idle"); }
  }

  const curve = result?.responseCurves[0] ?? null;
  return <section className="sensitivity-section" aria-labelledby="sensitivity-title">
    <div className="sensitivity-heading"><div><p className="section-eyebrow">{guided ? "Change one assumption at a time" : "One factor at a time"}</p><h2 id="sensitivity-title">{guided ? "Test different assumptions" : "Sensitivity"}</h2><p>{guided ? "Test how one assumption changes the result across selected values." : "Observe how one explicit assumption relates to one selected metric across a tested range."}</p></div><span className="sensitivity-work">{work.toLocaleString()} {guided ? "estimated simulation workload" : "work units"}</span></div>
    <div className="sensitivity-controls">
      <label>{guided ? "Type of assumption" : "Target category"}<select aria-label={guided ? "Type of assumption" : "Sensitivity target category"} value={category} onChange={(event) => { const next = targetEntries.find(([, target]) => target.category === event.target.value); if (next) { setTargetKey(next[0]); setResult(null); } }}>{[...new Set(targetEntries.map(([, target]) => target.category))].map((value) => <option key={value}>{value}</option>)}</select></label>
      <label>{guided ? "Part of the operation" : "Target entity"}<select aria-label={guided ? "Part of the operation" : "Sensitivity target entity"} value={targetKey} onChange={(event) => { setTargetKey(event.target.value as SensitivityTargetKey); setResult(null); }}>{categoryTargets.map(([key, target]) => <option value={key} key={key}>{target.entity}</option>)}</select></label>
      <label>{guided ? "Value to change" : "Target field"}<select aria-label={guided ? "Value to change" : "Sensitivity target field"} value={targetKey} onChange={(event) => { setTargetKey(event.target.value as SensitivityTargetKey); setResult(null); }}>{categoryTargets.map(([key, target]) => <option value={key} key={key}>{target.fieldLabel}</option>)}</select></label>
      <label>Tested values<input aria-label="Tested values" value={valueText} onChange={(event) => { setValueText(event.target.value); setResult(null); }} aria-invalid={Boolean(parsed.error || baselineMissing)} /></label>
      <label>{guided ? "Result to measure" : "Primary metric"}<select value={metric} onChange={(event) => { setMetric(event.target.value as SensitivityMetric); setResult(null); }}>{Object.entries(metricLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label>{guided ? "Matched tests per value" : "Sensitivity runs"}<select aria-label={guided ? "Matched tests per value" : "Sensitivity runs"} value={runs} onChange={(event) => { setRuns(Number(event.target.value) as 10 | 25 | 50 | 100); setResult(null); }}>{[10, 25, 50, 100].map((value) => <option key={value}>{value}</option>)}</select></label>
    </div>
    {(parsed.error || baselineMissing) && <p className="inline-error" role="alert">{parsed.error ?? `Include the baseline value ${baselineValue} explicitly.`}</p>}
    <button className="primary sensitivity-run" type="button" disabled={state === "running" || health !== "ready" || Boolean(parsed.error || baselineMissing) || work > 100000} onClick={submit}>{state === "running" ? "Running sensitivity…" : result ? "Run again" : "Run sensitivity"}</button>
    {error && <div className="sensitivity-error" role="alert"><strong>{error.code}</strong><p>{error.message}</p></div>}
    <SensitivityEvidence curve={curve} result={result} metric={metric} guided={guided} />
  </section>;
}

function SensitivityEvidence({ curve, result, metric, guided }: { curve: SensitivityCurve | null; result: SensitivityResult | null; metric: SensitivityMetric; guided: boolean }) {
  return <div className="sensitivity-evidence">
    <div className="sensitivity-curve"><h3>{guided ? "What happened" : "Observed response"}</h3>{curve ? <ResponseChart curve={curve} /> : <div className="sensitivity-empty">Run the explicit values to view the observed response.</div>}</div>
    <div className="sensitivity-reading"><span>{guided ? "Plain conclusion" : "Observed monotonicity"}</span><strong>{curve && guided ? sensitivityConclusion(curve.monotonicity, metricLabels[metric]) : curve ? curve.monotonicity.replaceAll("_", " ") : "Not available"}</strong>{guided && <small>Only explicit tested values are shown; the result does not establish the cause.</small>}<span>{guided ? "Result checks" : "Integrity"}</span><strong>{result ? `${result.integrity.status} · ${result.integrity.checksRun} checks` : "Not available"}</strong>{guided && <><span>How strongly the result changed</span><small>Available in technical sensitivity evidence.</small></>}</div>
    <table aria-label="Sensitivity response values"><caption>{metricLabels[metric]} across explicit tested values. No interpolation.</caption><thead><tr><th scope="col">Value</th><th scope="col">Status</th><th scope="col">Mean</th>{!guided && <><th scope="col">Confidence interval</th><th scope="col">Observed elasticity</th></>}</tr></thead><tbody>{curve ? curve.points.map((point) => <tr key={point.parameterValue}><th scope="row">{point.parameterValue}{point.isBaselineValue ? " · baseline" : ""}</th><td>{point.status}</td><td>{format(point.mean)}</td>{!guided && <><td>{point.confidenceIntervalLower === null ? "Not available" : `${format(point.confidenceIntervalLower)} – ${format(point.confidenceIntervalUpper)}`}</td><td>{format(point.observedElasticity)}</td></>}</tr>) : <tr><td colSpan={guided ? 3 : 5}>No sensitivity evidence yet.</td></tr>}</tbody></table>
    {curve && curve.finiteDifferences.length > 0 && <details><summary>Finite differences</summary><pre>{JSON.stringify(curve.finiteDifferences, null, 2)}</pre></details>}
    {curve && curve.thresholdCrossings.length > 0 && <details><summary>Observed threshold crossing intervals</summary><pre>{JSON.stringify(curve.thresholdCrossings, null, 2)}</pre></details>}
  </div>;
}

function sensitivityConclusion(monotonicity: string, metric: string): string {
  if (monotonicity === "observed_mixed") return `This experiment did not show that increasing the tested assumption consistently changed ${metric.toLowerCase()}. The tested results moved in different directions, which may indicate simulation variation or a constraint elsewhere in the process.`;
  if (monotonicity === "observed_increasing") return `Across the explicit tested values, ${metric.toLowerCase()} increased. This is an observed result, not a causal conclusion.`;
  if (monotonicity === "observed_decreasing") return `Across the explicit tested values, ${metric.toLowerCase()} decreased. This is an observed result, not a causal conclusion.`;
  if (monotonicity === "observed_flat") return `Across the explicit tested values, ${metric.toLowerCase()} remained effectively unchanged.`;
  return "There was not enough successful evidence to describe a consistent response.";
}

function ResponseChart({ curve }: { curve: SensitivityCurve }) {
  const valid = useMemo(() => curve.points.filter((point) => point.status === "valid" && point.mean !== null), [curve]);
  if (valid.length < 1) return <div className="sensitivity-empty">No successful response points.</div>;
  const xs = valid.map((point) => point.parameterValue); const ys = valid.map((point) => point.mean as number);
  const minX = Math.min(...xs); const maxX = Math.max(...xs); const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const x = (value: number) => 30 + (maxX === minX ? 0.5 : (value - minX) / (maxX - minX)) * 440;
  const y = (value: number) => 170 - (maxY === minY ? 0.5 : (value - minY) / (maxY - minY)) * 135;
  return <svg className="response-chart" viewBox="0 0 500 200" role="img" aria-label={`${curve.metric} observed at ${valid.length} explicit tested values. Straight segments connect adjacent successful points only.`}><path d="M30 170H475M30 20V170" className="chart-axis" />{valid.slice(0, -1).map((point, index) => { const next = valid[index + 1]; const adjacent = curve.points.findIndex((item) => item === next) - curve.points.findIndex((item) => item === point) === 1; return adjacent ? <line key={point.parameterValue} x1={x(point.parameterValue)} y1={y(point.mean as number)} x2={x(next.parameterValue)} y2={y(next.mean as number)} className="chart-segment" /> : null; })}{valid.map((point) => <g key={point.parameterValue}>{point.confidenceIntervalLower !== null && <line x1={x(point.parameterValue)} x2={x(point.parameterValue)} y1={y(point.confidenceIntervalLower)} y2={y(point.confidenceIntervalUpper as number)} className="chart-confidence" />}<circle cx={x(point.parameterValue)} cy={y(point.mean as number)} r={point.isBaselineValue ? 7 : 5} className={point.isBaselineValue ? "chart-point baseline" : "chart-point"} /><text x={x(point.parameterValue)} y="191" textAnchor="middle">{point.parameterValue}</text></g>)}</svg>;
}

const format = (value: number | null) => value === null ? "Not available" : value.toFixed(3);
