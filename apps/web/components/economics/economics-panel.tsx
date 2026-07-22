"use client";

import { useState } from "react";
import { runEconomicComparison, type ApiError, type EconomicComparisonResult } from "../../lib/api/simulation";
import { buildEconomicCsvExport, buildEconomicJsonExport } from "../../lib/economics/exports";
import { buildEconomicAssumptions, DEFAULT_ECONOMIC_DRAFT, interventionFor, validateEconomicDraft, type EconomicDraft } from "../../lib/economics/request-adapter";
import { downloadText } from "../../lib/scenario-lab/exports";
import { asRecord, asRecords } from "../../lib/scenario-lab/result-adapter";
import { buildScenario, type ScenarioDraft } from "../../lib/scenarios/builders";
import { buildBaseline, type BaselineForm } from "../../lib/templates/support";

type Objective = "averageCycleTime" | "p95CycleTime" | "slaAttainment" | "timeWeightedQueueLength";

export function EconomicsPanel({ baseline, scenarios, runs, objective, health, guided = false }: { baseline: BaselineForm; scenarios: ScenarioDraft[]; runs: number; objective: Objective; health: "checking" | "ready" | "unavailable"; guided?: boolean }) {
  const [draft, setDraft] = useState<EconomicDraft>({ ...DEFAULT_ECONOMIC_DRAFT });
  const [oneTime, setOneTime] = useState<Record<string, string>>({});
  const [periods, setPeriods] = useState<Record<string, string>>({});
  const [state, setState] = useState<"idle" | "running">("idle");
  const [result, setResult] = useState<EconomicComparisonResult | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const draftError = validateEconomicDraft(draft);
  const interventionError = scenarios.some((item) => { const cost = oneTime[item.id] ?? ""; const period = periods[item.id] ?? ""; return (cost !== "" && (!Number.isFinite(Number(cost)) || Number(cost) < 0)) || (period !== "" && (!Number.isInteger(Number(period)) || Number(period) < 1 || cost === "")); });
  const work = 100 * runs * (scenarios.length + 1);
  const update = (key: keyof EconomicDraft, value: string) => { setDraft({ ...draft, [key]: value }); setResult(null); };

  async function submit() {
    if (draftError || interventionError || state === "running") return;
    setState("running"); setResult(null); setError(null);
    const interventions = scenarios.map((item) => interventionFor(item.id, oneTime[item.id] ?? "", periods[item.id] ?? "")).filter((item) => item !== null);
    try {
      setResult(await runEconomicComparison({ schemaVersion: "0.7.0", comparison: {
        schemaVersion: "0.5.0", baselineModel: buildBaseline(baseline), scenarios: scenarios.map((item) => buildScenario(item, baseline)),
        execution: { baseSeed: 20260716, runCount: runs, confidenceLevel: 0.95, minimumSuccessfulRunRatio: 1, minimumPairedRunRatio: 1, observation: { warmupDuration: 0 }, thresholds: {} },
        objective: { metric: objective, direction: objective === "slaAttainment" ? "maximize" : "minimize" }, guardrails: [],
        representativeEvidence: { baseline: false, topRankedScenario: false, detailMode: "summary", sampledItemLimit: null },
      }, assumptions: buildEconomicAssumptions(draft), interventions }));
    } catch (caught) { setError(caught as ApiError); } finally { setState("idle"); }
  }

  return <section className="economics-section" aria-labelledby="economics-title">
    <div className="economics-heading"><div><p className="section-eyebrow">{guided ? "Costs you provide" : "Explicit supplied assumptions"}</p><h2 id="economics-title">{guided ? "Costs" : "Economics"}</h2><p>{guided ? "Add costs you know alongside the result to measure. OpsTwin does not infer costs or make a recommendation." : "Compare recurring operating cost evidence alongside the selected operational objective. This view does not infer costs or make a prescriptive intervention claim."}</p>{guided && <p className="economics-hint">Recurring costs are calculated for the simulated workload in each comparison run. They are not a real-world billing-period forecast.</p>}</div>{!guided && <span className="sensitivity-work">{work.toLocaleString()} work units</span>}</div>
    <div className="economics-grid"><div className="economics-editor"><h3>Cost assumptions</h3><div className="economics-fields">
      <EconomicInput label="Currency" value={draft.currency} onChange={(value) => update("currency", value.toUpperCase())} />
      <EconomicInput label={guided ? "General-support availability cost (currency per agent-minute; hourly equivalent is 60× this value)" : "Level 1 capacity / agent-minute"} value={draft.level1CapacityRate} onChange={(value) => update("level1CapacityRate", value)} />
      <EconomicInput label={guided ? "Specialist-support availability cost (currency per agent-minute; hourly equivalent is 60× this value)" : "Level 2 capacity / agent-minute"} value={draft.level2CapacityRate} onChange={(value) => update("level2CapacityRate", value)} />
      <EconomicInput label={guided ? "Cost each time a ticket is reviewed at triage" : "Triage visit"} value={draft.stageVisitRate} onChange={(value) => update("stageVisitRate", value)} />
      <EconomicInput label={guided ? "Cost of one ticket waiting for one minute" : "Queue item-minute"} value={draft.queueHoldingRate} onChange={(value) => update("queueHoldingRate", value)} />
      <EconomicInput label={guided ? "Cost assigned when a ticket misses the resolution target" : "SLA violation"} value={draft.slaViolationRate} onChange={(value) => update("slaViolationRate", value)} />
      <EconomicInput label={guided ? "Cost assigned when a ticket does not complete successfully" : "Terminal failure"} value={draft.terminalFailureRate} onChange={(value) => update("terminalFailureRate", value)} />
      <EconomicInput label={guided ? "Cost each time a ticket must be handled again" : "Rework"} value={draft.reworkRate} onChange={(value) => update("reworkRate", value)} />
      <EconomicInput label={guided ? "Fixed cost per configured analysis period" : "Fixed analysis period"} value={draft.fixedPeriodCost} onChange={(value) => update("fixedPeriodCost", value)} />
    </div>{draftError && <p className="inline-error" role="alert">{draftError}</p>}<p className="economics-hint">{guided ? "Leave a field blank when the cost is unknown. OpsTwin will not treat a missing value as zero." : "Blank means not configured. An explicit zero remains configured."}</p></div>
    <div className="economics-editor"><h3>{guided ? "Cost of making the change" : "Intervention costs"}</h3>{scenarios.map((item) => <fieldset key={item.id}><legend>{item.name}</legend><EconomicInput label={guided ? "Upfront cost" : "One-time cost"} value={oneTime[item.id] ?? ""} onChange={(value) => { setOneTime({ ...oneTime, [item.id]: value }); setResult(null); }} /><EconomicInput label={guided ? "Number of periods used to spread the upfront cost" : "Amortization periods"} value={periods[item.id] ?? ""} onChange={(value) => { setPeriods({ ...periods, [item.id]: value }); setResult(null); }} /></fieldset>)}{interventionError && <p className="inline-error" role="alert">Use a nonnegative one-time cost and a positive whole number of periods. Periods require a cost.</p>}<p className="economics-hint">One-time cost remains separate unless periods are explicit.</p></div></div>
    <button className="primary sensitivity-run" type="button" disabled={health !== "ready" || state === "running" || Boolean(draftError || interventionError) || work > 100000} onClick={submit}>{state === "running" ? "Running economic comparison…" : result ? "Run again" : "Run economic comparison"}</button>
    {error && <div className="sensitivity-error" role="alert"><strong>{error.code}</strong><p>{error.message}</p></div>}
    {result ? <EconomicEvidence result={result} /> : <div className="sensitivity-empty">Run with explicit assumptions to inspect recurring costs and operational trade-offs.</div>}
  </section>;
}

function EconomicInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label>{label}<input value={value} inputMode={label === "Currency" ? "text" : "decimal"} onChange={(event) => onChange(event.target.value)} placeholder={label === "Currency" ? "EUR" : "Not configured"} /></label>; }
function EconomicEvidence({ result }: { result: EconomicComparisonResult }) {
  return <div className="economic-evidence"><div className="economics-actions"><button className="secondary" type="button" onClick={() => downloadText("opstwin-economic-comparison.json", buildEconomicJsonExport(result), "application/json")}>Export JSON</button><button className="secondary" type="button" onClick={() => downloadText("opstwin-economic-comparison.csv", buildEconomicCsvExport(result), "text/csv")}>Export CSV</button></div><table aria-label="Economic comparison evidence"><caption>Recurring costs and the selected operational objective under supplied assumptions.</caption><thead><tr><th>Scenario</th><th>Recurring cost</th><th>Paired delta</th><th>Lower-cost probability</th><th>Operational relationship</th><th>Intervention</th></tr></thead><tbody>{asRecords(result.scenarios).map((scenario) => { const current = asRecord(scenario.scenarioCost); const delta = asRecord(scenario.recurringCostDelta); const intervention = asRecord(scenario.intervention); return <tr key={String(scenario.scenarioId)}><th scope="row">{String(scenario.scenarioName)}</th><td>{money(asRecord(current?.recurringOperatingCost)?.mean, result.currency)}</td><td>{money(asRecord(delta?.absoluteDelta)?.mean, result.currency)}</td><td>{percentage(scenario.probabilityLowerCost)}</td><td>{String(scenario.evidenceStatement)}</td><td>{intervention?.oneTimeCost === null ? "Not configured" : `${money(intervention?.oneTimeCost, result.currency)} one-time${intervention?.amortizedCostPerPeriod === null ? " · separate" : ` · ${money(intervention?.amortizedCostPerPeriod, result.currency)} per period`}`}</td></tr>; })}</tbody></table><details><summary>Technical economic evidence</summary><dl><div><dt>Contract</dt><dd>{result.schemaVersion}</dd></div><div><dt>Currency</dt><dd>{result.currency}</dd></div><div><dt>Time unit</dt><dd>{result.modelTimeUnit}</dd></div><div><dt>Cost snapshots</dt><dd>{String(result.execution.economicSnapshotEvaluations)}</dd></div><div><dt>Ordinary retained events</dt><dd>{String(result.execution.ordinaryRunRetainedEventCount)}</dd></div><div><dt>Integrity</dt><dd>{result.integrity.status} · {result.integrity.checksRun} checks</dd></div></dl></details></div>;
}
const money = (value: unknown, currency: string) => typeof value === "number" && Number.isFinite(value) ? `${currency} ${value.toFixed(2)}` : "Not available";
const percentage = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(0)}%` : "Not available";
