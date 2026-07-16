/* eslint-disable @next/next/no-html-link-for-pages -- document-level wordmark */
"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { WorkflowVisualization } from "../../components/workflow/workflow-map";
import { SensitivityPanel } from "../../components/sensitivity/sensitivity-panel";
import { EconomicsPanel } from "../../components/economics/economics-panel";
import { checkSimulationHealth, runScenarioComparison, type ApiError, type ComparisonResult } from "../../lib/api/simulation";
import { buildCsvExport, buildJsonExport, downloadText } from "../../lib/scenario-lab/exports";
import { buildGuardrail, guardrailOptions, validateGuardrail, type GuardrailDraft, type GuardrailMetric } from "../../lib/scenario-lab/guardrails";
import { coreMetricKeys, finiteNumber, formatMetric, formatRelative, metricRegistry, type MetricCategory, type MetricKey } from "../../lib/scenario-lab/metrics";
import { asRecord, asRecords, confidence, getScenarioStatus, guardrailCopy, pairedMetric, rankingFor, type UnknownRecord } from "../../lib/scenario-lab/result-adapter";
import { isLatestRequest } from "../../lib/scenario-lab/request-lifecycle";
import { deleteScenario, duplicateScenario, moveScenario } from "../../lib/scenario-lab/scenario-state";
import { buildScenario, estimateWork, validateScenarios, type ScenarioDraft, type ScenarioType } from "../../lib/scenarios/builders";
import { buildBaseline, DEFAULT_FORM, type BaselineForm } from "../../lib/templates/support";

const fields: { key: keyof BaselineForm; label: string; unit: string; min: number; max: number; step: number }[] = [
  { key: "arrivalInterval", label: "Mean arrival interval", unit: "minutes", min: 0.1, max: 60, step: 0.1 },
  { key: "triageDuration", label: "Triage mean duration", unit: "minutes", min: 0.1, max: 60, step: 0.1 },
  { key: "level1Capacity", label: "Level 1 capacity", unit: "agents", min: 1, max: 50, step: 1 },
  { key: "level2Capacity", label: "Level 2 capacity", unit: "agents", min: 1, max: 50, step: 1 },
  { key: "qualityDuration", label: "Quality-check duration", unit: "minutes", min: 0.1, max: 60, step: 0.1 },
  { key: "escalationProbability", label: "Escalation probability", unit: "%", min: 0, max: 100, step: 1 },
  { key: "reworkProbability", label: "Rework probability", unit: "%", min: 0, max: 100, step: 1 },
  { key: "slaTarget", label: "SLA target", unit: "minutes", min: 1, max: 1440, step: 1 },
];

const scenarioLabels: Record<ScenarioType, string> = {
  demand: "Demand increase",
  level1Staffing: "Level 1 staffing",
  level2Staffing: "Level 2 staffing",
  triageProcess: "Triage processing",
  quality: "Quality and rework",
};
const scenarioInputLabels: Record<ScenarioType, string> = {
  demand: "Demand increase (%)",
  level1Staffing: "Level 1 agents added",
  level2Staffing: "Level 2 agents added",
  triageProcess: "Triage time reduction (%)",
  quality: "Rework reduction (%)",
};
const objectives = { averageCycleTime: "Average cycle time", p95CycleTime: "P95 cycle time", slaAttainment: "SLA attainment", timeWeightedQueueLength: "Queue length" } as const;
type Objective = keyof typeof objectives;
type AnalysisView = "overview" | "metrics" | "risk" | "resources" | "technical";
const analysisViews: { id: AnalysisView; label: string }[] = [{ id: "overview", label: "Overview" }, { id: "metrics", label: "Metrics" }, { id: "risk", label: "Risk" }, { id: "resources", label: "Resources" }, { id: "technical", label: "Technical evidence" }];
const metricCategories: MetricCategory[] = ["Service", "Flow", "Risk", "Resources"];
const defaultScenarios: ScenarioDraft[] = [
  { id: "scenario-1", name: "Add one Level 1 agent", type: "level1Staffing", value: 1 },
  { id: "scenario-2", name: "Faster triage", type: "triageProcess", value: 25 },
];

const objectiveDirection = (objective: Objective) => objective === "slaAttainment" ? "maximize" : "minimize";
const scenarioSummary = (scenario: ScenarioDraft) => `${scenarioInputLabels[scenario.type]}: ${scenario.value}${scenario.type === "level1Staffing" || scenario.type === "level2Staffing" ? "" : "%"}`;
const meanFrom = (metrics: unknown, key: string) => finiteNumber(asRecord(asRecord(metrics)?.[key])?.mean);
const scenarioResult = (result: ComparisonResult | null, id: string) => result ? asRecords(result.scenarios).find((item) => item.scenarioId === id) ?? null : null;
const errorTitle = (code: string) => code.toLowerCase().replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());

export function Workspace() {
  const [baseline, setBaseline] = useState<BaselineForm>({ ...DEFAULT_FORM });
  const [scenarios, setScenarios] = useState<ScenarioDraft[]>(defaultScenarios);
  const [runs, setRuns] = useState(50);
  const [objective, setObjective] = useState<Objective>("averageCycleTime");
  const [guardrail, setGuardrail] = useState<GuardrailDraft>({ enabled: false, metric: "slaAttainment", value: 75 });
  const [health, setHealth] = useState<"checking" | "ready" | "unavailable">("checking");
  const [state, setState] = useState<"idle" | "running">("idle");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [analysisView, setAnalysisView] = useState<AnalysisView>("overview");
  const [metricCategory, setMetricCategory] = useState<MetricCategory>("Service");
  const controller = useRef<AbortController | null>(null);
  const requestIdentity = useRef(0);
  const resultRegion = useRef<HTMLElement | null>(null);
  const errorRegion = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    checkSimulationHealth().then((ok) => setHealth(ok ? "ready" : "unavailable")).catch(() => setHealth("unavailable"));
    return () => controller.current?.abort();
  }, []);

  const work = estimateWork(100, runs, scenarios.length);
  const scenarioError = validateScenarios(scenarios);
  const guardrailError = validateGuardrail(guardrail);
  const baselineError = fields.find((field) => !Number.isFinite(baseline[field.key]) || baseline[field.key] < field.min || baseline[field.key] > field.max);

  function invalidateEvidence() {
    setResult(null);
    setError(null);
    setAnnouncement("");
  }

  function updateScenario(id: string, patchValue: Partial<ScenarioDraft>) {
    setScenarios((items) => items.map((item) => item.id === id ? { ...item, ...patchValue } : item));
    invalidateEvidence();
  }

  function removeScenario(id: string, index: number) {
    setScenarios((items) => deleteScenario(items, id));
    invalidateEvidence();
    window.requestAnimationFrame(() => {
      const next = document.querySelector<HTMLButtonElement>(`[data-scenario-index="${Math.max(0, index - 1)}"] .scenario-edit`) ?? document.querySelector<HTMLButtonElement>(".add-scenario");
      next?.focus();
    });
  }

  function copyScenario(id: string) {
    setScenarios((items) => duplicateScenario(items, id));
    invalidateEvidence();
  }

  async function submit() {
    if (state === "running" || baselineError || scenarioError || guardrailError || work > 30000) return;
    const identity = ++requestIdentity.current;
    const active = new AbortController();
    controller.current = active;
    setState("running");
    setError(null);
    setResult(null);
    setAnnouncement("");
    const payload = {
      schemaVersion: "0.5.0",
      baselineModel: buildBaseline(baseline),
      scenarios: scenarios.map((item) => buildScenario(item, baseline)),
      execution: {
        baseSeed: 20260716,
        runCount: runs,
        confidenceLevel: 0.95,
        minimumSuccessfulRunRatio: 1,
        minimumPairedRunRatio: 1,
        observation: { warmupDuration: 0 },
        thresholds: { minimumSlaAttainment: 0.8, maximumAverageCycleTime: baseline.slaTarget },
      },
      objective: { metric: objective, direction: objectiveDirection(objective) },
      guardrails: buildGuardrail(guardrail),
      representativeEvidence: { baseline: true, topRankedScenario: true, detailMode: "sampled", sampledItemLimit: 25 },
    };
    try {
      const nextResult = await runScenarioComparison(payload, active.signal);
      if (!isLatestRequest(requestIdentity.current, identity)) return;
      setResult(nextResult);
      setAnalysisView("overview");
      setAnnouncement(`Comparison complete. ${nextResult.scenarios.length} scenario results are available.`);
      window.requestAnimationFrame(() => resultRegion.current?.focus());
    } catch (caught) {
      if (!isLatestRequest(requestIdentity.current, identity)) return;
      const object = asRecord(caught);
      const nextError = object && typeof object.code === "string" && typeof object.message === "string" ? caught as ApiError : { code: "UNKNOWN_SERVER_ERROR", message: "The comparison could not be completed. Your inputs have been preserved.", fieldErrors: [], details: {} };
      setError(nextError);
      setAnnouncement(`Comparison failed. ${nextError.message}`);
      window.requestAnimationFrame(() => errorRegion.current?.focus());
    } finally {
      if (isLatestRequest(requestIdentity.current, identity)) {
        setState("idle");
        controller.current = null;
      }
    }
  }

  function selectAnalysisView(view: AnalysisView, event?: KeyboardEvent<HTMLButtonElement>) {
    if (!event) { setAnalysisView(view); return; }
    const current = analysisViews.findIndex((item) => item.id === view);
    const key = event.key;
    let next = current;
    if (key === "ArrowRight") next = (current + 1) % analysisViews.length;
    else if (key === "ArrowLeft") next = (current - 1 + analysisViews.length) % analysisViews.length;
    else if (key === "Home") next = 0;
    else if (key === "End") next = analysisViews.length - 1;
    else return;
    event.preventDefault();
    setAnalysisView(analysisViews[next].id);
    document.getElementById(`analysis-tab-${analysisViews[next].id}`)?.focus();
  }

  return <main className="site-shell workspace-shell">
    <header className="masthead"><a className="wordmark" href="/">OpsTwin</a><span className={`service-status ${health}`}>Simulation service: {health}</span></header>
    <div className="workspace-intro"><div><p className="eyebrow">Scenario Lab · Support operations</p><h1>Trace the trade-offs.</h1></div><p>Organize a small scenario set, run paired futures, and inspect server-calculated evidence across service, flow, risk, and resources.</p></div>
    <div className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</div>
    <section className="lab-layout" aria-label="Scenario Lab">
      <div className="configuration-column">
        <section className="lab-section baseline-section" aria-labelledby="baseline-title">
          <SectionHeading number="01" eyebrow="Immutable reference" title="Baseline" id="baseline-title" copy="A 100-ticket support workflow. Display assumptions map to a fresh model copy for each comparison." />
          <div className="field-grid">{fields.map((field) => {
            const invalid = !Number.isFinite(baseline[field.key]) || baseline[field.key] < field.min || baseline[field.key] > field.max;
            return <label key={field.key}>{field.label}<span className="input-unit"><input aria-label={field.label} aria-invalid={invalid} aria-describedby={`${field.key}-hint${invalid ? ` ${field.key}-error` : ""}`} type="number" min={field.min} max={field.max} step={field.step} value={baseline[field.key]} onChange={(event) => { setBaseline({ ...baseline, [field.key]: Number(event.target.value) }); invalidateEvidence(); }} /><small>{field.unit}</small></span><span id={`${field.key}-hint`} className="hint">{field.min}–{field.max} {field.unit}</span>{invalid && <span id={`${field.key}-error`} className="field-error">Enter a value in the documented range.</span>}</label>;
          })}</div>
          {baselineError && <p className="inline-error" role="alert">{baselineError.label} must be between {baselineError.min} and {baselineError.max}.</p>}
        </section>

        <section className="lab-section" aria-labelledby="scenario-title">
          <div className="section-heading"><SectionHeading number="02" eyebrow="Maximum three" title="Scenario set" id="scenario-title" copy="Each card is a session-local intervention. Display order stays separate from backend ranking." /><button className="secondary add-scenario" type="button" onClick={() => { setScenarios((items) => items.length >= 3 ? items : [...items, { id: globalThis.crypto?.randomUUID?.() ?? `scenario-${Date.now()}`, name: "Demand change", type: "demand", value: 10 }]); invalidateEvidence(); }} disabled={scenarios.length >= 3}>Add scenario</button></div>
          <div className="scenario-list">{scenarios.map((item, index) => {
            const evidence = scenarioResult(result, item.id);
            const ranking = result ? rankingFor(result, item.id) : null;
            const valid = Boolean(item.name.trim()) && Number.isFinite(item.value) && item.value > 0;
            return <article className="scenario-card" key={item.id} data-scenario-index={index} aria-labelledby={`${item.id}-title`}>
              <div className="scenario-card-head"><div><span className={`status-dot ${valid ? "valid" : "invalid"}`}>{valid ? "Ready to compare" : "Needs attention"}</span><h3 id={`${item.id}-title`}>{item.name.trim() || `Scenario ${index + 1}`}</h3><p>{scenarioLabels[item.type]} · 1 override</p></div><span className="scenario-index">{String(index + 1).padStart(2, "0")}</span></div>
              <p className="intervention-summary">{scenarioSummary(item)}</p>
              <div className="scenario-editor">
                <label htmlFor={`${item.id}-name`}>Scenario name</label><input id={`${item.id}-name`} aria-invalid={!item.name.trim()} aria-describedby={!item.name.trim() ? `${item.id}-name-error` : undefined} value={item.name} onChange={(event) => updateScenario(item.id, { name: event.target.value })} />{!item.name.trim() && <span className="field-error" id={`${item.id}-name-error`}>Scenario name cannot be empty.</span>}
                <div className="scenario-fields"><label>Scenario type<select value={item.type} onChange={(event) => updateScenario(item.id, { type: event.target.value as ScenarioType })}>{Object.entries(scenarioLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>{scenarioInputLabels[item.type]}<input type="number" min="1" max="100" aria-invalid={!Number.isFinite(item.value) || item.value <= 0} value={item.value} onChange={(event) => updateScenario(item.id, { value: Number(event.target.value) })} /></label></div>
              </div>
              {evidence && <div className="scenario-result-status"><strong>{getScenarioStatus(evidence, ranking)}</strong>{finiteNumber(ranking?.rank) !== null && <span>Rank {String(ranking?.rank)}</span>}<span>{guardrailCopy(evidence)}</span></div>}
              <div className="scenario-actions" aria-label={`Actions for ${item.name || `scenario ${index + 1}`}`}><button className="text-button scenario-edit" type="button" onClick={() => document.getElementById(`${item.id}-name`)?.focus()}>Edit</button><button className="text-button" type="button" onClick={() => copyScenario(item.id)} disabled={scenarios.length >= 3}>Duplicate</button><button className="text-button" type="button" aria-label={`Move ${item.name || `scenario ${index + 1}`} up`} onClick={() => { setScenarios((items) => moveScenario(items, item.id, -1)); invalidateEvidence(); }} disabled={index === 0}>Move up</button><button className="text-button" type="button" aria-label={`Move ${item.name || `scenario ${index + 1}`} down`} onClick={() => { setScenarios((items) => moveScenario(items, item.id, 1)); invalidateEvidence(); }} disabled={index === scenarios.length - 1}>Move down</button><button className="text-button danger" type="button" onClick={() => removeScenario(item.id, index)}>Delete</button></div>
            </article>;
          })}</div>
          {scenarioError && <p className="inline-error" role="alert">{scenarioError}</p>}
        </section>

        <section className="lab-section" aria-labelledby="settings-title">
          <SectionHeading number="03" eyebrow="Shared seed schedule" title="Execution settings" id="settings-title" copy="Choose the comparison lens and optional operating boundary. The backend evaluates eligibility." />
          <div className="settings-row"><label>Objective<select value={objective} onChange={(event) => { setObjective(event.target.value as Objective); invalidateEvidence(); }}>{Object.entries(objectives).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Paired runs<select value={runs} onChange={(event) => { setRuns(Number(event.target.value)); invalidateEvidence(); }}>{[10, 25, 50, 100].map((count) => <option key={count}>{count}</option>)}</select></label></div>
          <fieldset className="guardrail-control"><legend>Optional guardrail</legend><label className="toggle-row"><input type="checkbox" checked={guardrail.enabled} onChange={(event) => { setGuardrail({ ...guardrail, enabled: event.target.checked }); invalidateEvidence(); }} /><span>Evaluate one eligibility guardrail</span></label>{guardrail.enabled && <div className="guardrail-fields"><label>Guardrail metric<select value={guardrail.metric} onChange={(event) => { const metric = event.target.value as GuardrailMetric; setGuardrail({ ...guardrail, metric, value: metric === "slaAttainment" || metric === "resourcePoolUtilization" ? 75 : 60, resourcePoolId: metric === "resourcePoolUtilization" ? "level-1-agents" : undefined }); invalidateEvidence(); }}>{Object.entries(guardrailOptions).map(([value, option]) => <option key={value} value={value}>{option.label}</option>)}</select></label>{guardrail.metric === "resourcePoolUtilization" && <label>Resource pool<select value={guardrail.resourcePoolId} onChange={(event) => { setGuardrail({ ...guardrail, resourcePoolId: event.target.value }); invalidateEvidence(); }}><option value="level-1-agents">Level 1 agents</option><option value="level-2-agents">Level 2 agents</option><option value="triage-team">Triage team</option><option value="quality-team">Quality team</option></select></label>}<label>{guardrailOptions[guardrail.metric].label}<span className="input-unit"><input type="number" aria-invalid={Boolean(guardrailError)} aria-describedby={guardrailError ? "guardrail-error" : "guardrail-unit"} min={guardrailOptions[guardrail.metric].minimum} max={guardrailOptions[guardrail.metric].maximum} value={guardrail.value} onChange={(event) => { setGuardrail({ ...guardrail, value: Number(event.target.value) }); invalidateEvidence(); }} /><small id="guardrail-unit">{guardrailOptions[guardrail.metric].unit}</small></span></label></div>}{guardrailError && <p id="guardrail-error" className="inline-error" role="alert">{guardrailError}</p>}{!guardrail.enabled && <p className="guardrail-empty">No guardrails configured</p>}</fieldset>
          <div className={`work-meter ${work > 30000 ? "over" : ""}`}><span>Estimated work</span><strong>{work.toLocaleString()} / 30,000 item executions</strong></div>{work > 30000 && <p className="inline-error" role="alert">Reduce runs or scenarios to stay within the product work guard.</p>}
          <details><summary>Advanced evidence settings</summary><dl><div><dt>Base seed</dt><dd>20260716</dd></div><div><dt>Confidence</dt><dd>95%</dd></div><div><dt>Representative detail</dt><dd>Sampled · 25 items</dd></div><div><dt>Risk thresholds</dt><dd>80% SLA · baseline SLA target</dd></div></dl></details>
        </section>
      </div>

      <aside className="run-panel" aria-labelledby="run-title"><span className="step-number">04</span><p className="panel-kicker">Ready when inputs are valid</p><h2 id="run-title">Run comparison</h2><p>One baseline and each scenario use the same child seed at every paired index.</p><button className="primary" type="button" onClick={submit} disabled={state === "running" || health === "unavailable" || Boolean(baselineError || scenarioError || guardrailError) || work > 30000}>{state === "running" ? "Running comparison…" : result ? "Run again" : "Run paired comparison"}</button>{state === "running" && <><p className="live-status" aria-live="polite">Running {runs} paired simulations for {scenarios.length} scenarios.</p><button className="secondary full" type="button" onClick={() => controller.current?.abort()}>Stop waiting</button></>}{error && <div className="error-panel" role="alert" tabIndex={-1} ref={errorRegion}><strong>{errorTitle(error.code)}</strong><p>{error.message}</p><button className="secondary full" type="button" onClick={submit}>Retry comparison</button></div>}<dl className="run-facts"><div><dt>Scenarios</dt><dd>{scenarios.length} / 3</dd></div><div><dt>Paired runs</dt><dd>{runs}</dd></div><div><dt>Objective</dt><dd>{objectives[objective]}</dd></div></dl></aside>
    </section>
    <WorkflowVisualization model={buildBaseline(baseline)} baseline={baseline} scenarios={scenarios} result={result} />
    <SensitivityPanel baseline={baseline} health={health} />
    <EconomicsPanel baseline={baseline} scenarios={scenarios} runs={runs} objective={objective} health={health} />
    {result && <Results result={result} baseline={baseline} scenarios={scenarios} settings={{ runs, objective, guardrail }} view={analysisView} setView={selectAnalysisView} metricCategory={metricCategory} setMetricCategory={setMetricCategory} regionRef={resultRegion} />}
  </main>;
}

function SectionHeading({ number, eyebrow, title, id, copy }: { number: string; eyebrow: string; title: string; id: string; copy: string }) {
  return <div className="section-title"><span className="step-number">{number}</span><div><p className="section-eyebrow">{eyebrow}</p><h2 id={id}>{title}</h2><p className="section-copy">{copy}</p></div></div>;
}

function Results({ result, baseline, scenarios, settings, view, setView, metricCategory, setMetricCategory, regionRef }: { result: ComparisonResult; baseline: BaselineForm; scenarios: ScenarioDraft[]; settings: unknown; view: AnalysisView; setView: (view: AnalysisView, event?: KeyboardEvent<HTMLButtonElement>) => void; metricCategory: MetricCategory; setMetricCategory: (category: MetricCategory) => void; regionRef: React.RefObject<HTMLElement | null> }) {
  const topRanking = asRecord(result.ranking[0]);
  const topId = typeof topRanking?.scenarioId === "string" ? topRanking.scenarioId : null;
  const topScenario = topId ? asRecords(result.scenarios).find((item) => item.scenarioId === topId) ?? null : null;
  const eligibleCount = asRecords(result.scenarios).filter((item) => item.eligible === true).length;
  const failedOrIneligibleCount = result.scenarios.length - eligibleCount;
  const settingsRecord = asRecord(settings);
  const exportJson = () => downloadText("opstwin-scenario-lab.json", buildJsonExport({ baseline, scenarios, settings, result }), "application/json");
  const exportCsv = () => downloadText("opstwin-scenario-summary.csv", buildCsvExport(result), "text/csv;charset=utf-8");
  return <section className="analysis" aria-labelledby="analysis-title" tabIndex={-1} ref={regionRef}>
    <div className="analysis-heading"><div><p className="eyebrow">Comparison evidence</p><h2 id="analysis-title">Analysis</h2><p>Backend ranking order and supplied evidence are preserved.</p></div><div className="analysis-actions"><button className="secondary" type="button" onClick={exportJson}>Export JSON</button><button className="secondary" type="button" onClick={exportCsv}>Export CSV</button><button className="secondary" type="button" onClick={() => window.print()}>Print summary</button></div></div>
    <div className="analysis-tabs" role="tablist" aria-label="Analysis sections">{analysisViews.map((item) => <button key={item.id} id={`analysis-tab-${item.id}`} type="button" role="tab" aria-selected={view === item.id} aria-controls={`analysis-panel-${item.id}`} tabIndex={view === item.id ? 0 : -1} onClick={() => setView(item.id)} onKeyDown={(event) => setView(item.id, event)}>{item.label}</button>)}</div>
    <div id={`analysis-panel-${view}`} role="tabpanel" aria-labelledby={`analysis-tab-${view}`}>
      {view === "overview" && <Overview result={result} topRanking={topRanking} topScenario={topScenario} eligibleCount={eligibleCount} failedOrIneligibleCount={failedOrIneligibleCount} />}
      {view === "metrics" && <MetricsView result={result} category={metricCategory} setCategory={setMetricCategory} />}
      {view === "risk" && <RiskView result={result} />}
      {view === "resources" && <ResourceView result={result} />}
      {view === "technical" && <TechnicalView result={result} scenarioDrafts={scenarios} />}
    </div>
    <PrintSummary result={result} baseline={baseline} objective={String(asRecord(result.objective)?.metric ?? settingsRecord?.objective ?? "Not available")} />
  </section>;
}

function Overview({ result, topRanking, topScenario, eligibleCount, failedOrIneligibleCount }: { result: ComparisonResult; topRanking: UnknownRecord | null; topScenario: UnknownRecord | null; eligibleCount: number; failedOrIneligibleCount: number }) {
  const objective = String(asRecord(result.objective)?.metric ?? "selected objective");
  const improvement = topScenario ? asRecord(pairedMetric(topScenario, objective as MetricKey)?.improvement) : null;
  const firstRisk = topScenario ? asRecords(topScenario.riskComparisons)[0] : null;
  return <div className="overview-view">
    <div className="overview-lead"><div><span className="status-label">Comparative ranking</span><h3>{topScenario ? "Ranked first under the selected objective" : "No scenario satisfied the current comparison requirements."}</h3><p>{topScenario ? String(topScenario.scenarioName ?? topScenario.scenarioId) : "Failed and ineligible scenarios remain available in the analysis."}</p></div><span className="integrity-badge">Integrity {result.integrity.status} · {result.integrity.checksRun} checks</span></div>
    <div className="summary-grid"><SummaryValue label="Selected objective" value={metricRegistry[objective as MetricKey]?.label ?? objective} /><SummaryValue label="Valid paired runs" value={topScenario ? String(topScenario.pairedRunCount ?? "Not available") : "Not available"} /><SummaryValue label="Scenarios" value={String(result.scenarios.length)} /><SummaryValue label="Eligible" value={String(eligibleCount)} /><SummaryValue label="Failed or ineligible" value={String(failedOrIneligibleCount)} /><SummaryValue label="Objective mean delta" value={topRanking ? formatMetric(objective as MetricKey, topRanking.objectiveMeanDelta) : "Not available"} /><SummaryValue label="Probability of improvement" value={formatMetric("probabilityOfImprovement", improvement?.probabilityOfImprovement ?? topRanking?.probabilityOfImprovement)} /><SummaryValue label="Guardrail" value={topScenario ? guardrailCopy(topScenario) : "Result unavailable"} /></div>
    <div className="overview-note"><span>Most relevant risk change</span><strong>{firstRisk ? `${metricRegistry[String(firstRisk.metric) as MetricKey]?.label ?? String(firstRisk.metric)}: ${formatPercentagePoints(firstRisk.probabilityPointChange)}` : "No risk threshold configured for this metric."}</strong></div>
    {topScenario && <div className="overview-evidence"><h3>Objective evidence</h3><ProbabilityView metric={objective as MetricKey} paired={pairedMetric(topScenario, objective as MetricKey)} /><ConfidenceInterval metric={objective as MetricKey} paired={pairedMetric(topScenario, objective as MetricKey)} /></div>}
  </div>;
}

function SummaryValue({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }

function MetricsView({ result, category, setCategory }: { result: ComparisonResult; category: MetricCategory; setCategory: (category: MetricCategory) => void }) {
  const baselineMetrics = asRecord(result.baseline.systemMetrics);
  const metrics = coreMetricKeys.filter((key) => metricRegistry[key].category === category);
  return <div className="metrics-view"><div className="category-filters" aria-label="Metric category filter">{metricCategories.map((item) => <button key={item} type="button" aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div>{category === "Resources" ? <ResourceView result={result} embedded /> : <><div className="metric-matrix-wrap"><table className="metric-matrix"><caption>{category} metric comparison. All deltas and intervals are returned by the backend.</caption><thead><tr><th scope="col">Metric</th><th scope="col">Scenario</th><th scope="col">Baseline</th><th scope="col">Scenario value</th><th scope="col">Mean paired delta</th><th scope="col">Relative delta</th><th scope="col">Probability</th><th scope="col">Confidence interval</th></tr></thead><tbody>{metrics.flatMap((key) => asRecords(result.scenarios).map((scenario, index) => {
    const paired = pairedMetric(scenario, key); const variant = asRecord(scenario.variant); const ranking = rankingFor(result, String(scenario.scenarioId));
    return <tr key={`${key}-${String(scenario.scenarioId)}`}><th scope="row">{index === 0 ? metricRegistry[key].label : <span className="visually-muted">{metricRegistry[key].label}</span>}<small>{metricRegistry[key].betterDirection}</small></th><th scope="row">{String(scenario.scenarioName ?? scenario.scenarioId)}<small>{getScenarioStatus(scenario, ranking)}</small></th><td>{formatMetric(key, meanFrom(baselineMetrics, key))}</td><td>{formatMetric(key, meanFrom(variant?.systemMetrics, key))}</td><td>{formatMetric(key, asRecord(paired?.absoluteDelta)?.mean)}</td><td>{formatRelative(asRecord(paired?.relativeDelta)?.mean)}</td><td><ProbabilityView metric={key} paired={paired} compact /></td><td><ConfidenceInterval metric={key} paired={paired} compact /></td></tr>;
  }))}</tbody></table></div><MetricMobileCards result={result} metrics={metrics} baselineMetrics={baselineMetrics} /></>}</div>;
}

function MetricMobileCards({ result, metrics, baselineMetrics }: { result: ComparisonResult; metrics: MetricKey[]; baselineMetrics: UnknownRecord | null }) {
  return <div className="metric-mobile" aria-label="Stacked scenario metric groups">{asRecords(result.scenarios).map((scenario) => <section key={String(scenario.scenarioId)}><h3>{String(scenario.scenarioName ?? scenario.scenarioId)}</h3>{metrics.map((key) => { const paired = pairedMetric(scenario, key); const variant = asRecord(scenario.variant); return <article key={key}><h4>{metricRegistry[key].label}</h4><dl><ResourceValue label="Baseline" value={formatMetric(key, meanFrom(baselineMetrics, key))} /><ResourceValue label="Scenario" value={formatMetric(key, meanFrom(variant?.systemMetrics, key))} /><ResourceValue label="Mean paired delta" value={formatMetric(key, asRecord(paired?.absoluteDelta)?.mean)} /><ResourceValue label="Relative delta" value={formatRelative(asRecord(paired?.relativeDelta)?.mean)} /></dl><ProbabilityView metric={key} paired={paired} /><ConfidenceInterval metric={key} paired={paired} /></article>; })}</section>)}</div>;
}

function ConfidenceInterval({ metric, paired, compact = false }: { metric: MetricKey; paired: UnknownRecord | null; compact?: boolean }) {
  const absolute = asRecord(paired?.absoluteDelta); const interval = confidence(paired); const lower = finiteNumber(interval?.lower); const mean = finiteNumber(absolute?.mean); const upper = finiteNumber(interval?.upper);
  if (lower === null || mean === null || upper === null) return <span className="unavailable">Not available</span>;
  const reliable = interval?.reliableSampleSize === true; const level = finiteNumber(interval?.level);
  return <div className={`interval ${compact ? "compact" : ""}`} aria-label={`${metricRegistry[metric].label} paired mean confidence interval: lower ${formatMetric(metric, lower)}, mean ${formatMetric(metric, mean)}, upper ${formatMetric(metric, upper)}, confidence ${level === null ? "not available" : `${level * 100}%`}, ${reliable ? "reliable sample size" : "small-sample reliability warning"}.`}><div className="interval-track" aria-hidden="true"><span className="interval-line" /><span className="interval-mean" /></div><div className="interval-values"><span>{formatMetric(metric, lower)}<small>lower</small></span><strong>{formatMetric(metric, mean)}<small>mean</small></strong><span>{formatMetric(metric, upper)}<small>upper</small></span></div><p>{level === null ? "Confidence unavailable" : `${(level * 100).toFixed(0)}% confidence`} · {reliable ? "Reliable sample size" : "Small-sample reliability warning"}</p>{!compact && <small>Normal approximation of the paired mean; not a full outcome range.</small>}</div>;
}

function ProbabilityView({ metric, paired, compact = false }: { metric: MetricKey; paired: UnknownRecord | null; compact?: boolean }) {
  const improvement = asRecord(paired?.improvement); const improved = finiteNumber(improvement?.probabilityOfImprovement); const degraded = finiteNumber(improvement?.probabilityOfDegradation); const tied = finiteNumber(improvement?.probabilityOfTie);
  if (improved === null || degraded === null || tied === null) return <span className="unavailable">Not available</span>;
  const label = `${metricRegistry[metric].label}: improved ${(improved * 100).toFixed(1)}%, degraded ${(degraded * 100).toFixed(1)}%, tied ${(tied * 100).toFixed(1)}%.`;
  return <div className={`probability-view ${compact ? "compact" : ""}`} aria-label={label}><div className="probability-bar" aria-hidden="true"><span className="improved" style={{ width: `${Math.max(0, Math.min(100, improved * 100))}%` }} /><span className="degraded" style={{ width: `${Math.max(0, Math.min(100, degraded * 100))}%` }} /><span className="tied" style={{ width: `${Math.max(0, Math.min(100, tied * 100))}%` }} /></div><div className="probability-values"><span>Improved <strong>{(improved * 100).toFixed(1)}%</strong>{!compact && finiteNumber(improvement?.improvedCount) !== null && <small>{String(improvement?.improvedCount)} runs</small>}</span><span>Degraded <strong>{(degraded * 100).toFixed(1)}%</strong>{!compact && finiteNumber(improvement?.degradedCount) !== null && <small>{String(improvement?.degradedCount)} runs</small>}</span><span>Tied <strong>{(tied * 100).toFixed(1)}%</strong>{!compact && finiteNumber(improvement?.tiedCount) !== null && <small>{String(improvement?.tiedCount)} runs</small>}</span></div></div>;
}

function RiskView({ result }: { result: ComparisonResult }) {
  const hasRisk = asRecords(result.scenarios).some((scenario) => asRecords(scenario.riskComparisons).length > 0);
  return <div className="risk-view"><div className="view-intro"><p className="section-eyebrow">Paired threshold evidence</p><h3>Operational risk transitions</h3><p>Violation probabilities and transitions are supplied by the comparison service. Percentage-point differences are factual, not causal claims.</p></div>{!hasRisk && <p className="empty-state">No risk threshold configured for this metric.</p>}{asRecords(result.scenarios).map((scenario) => <section className="risk-scenario" key={String(scenario.scenarioId)}><h3>{String(scenario.scenarioName ?? scenario.scenarioId)}</h3>{asRecords(scenario.riskComparisons).map((risk) => <article className="risk-card" key={String(risk.metric)}><div className="risk-summary"><div><span>{metricRegistry[String(risk.metric) as MetricKey]?.label ?? String(risk.metric)}</span><strong>Threshold {formatRiskThreshold(String(risk.metric), risk.threshold)}</strong></div><SummaryValue label="Baseline violation" value={formatMetric("riskProbability", risk.baselineProbability)} /><SummaryValue label="Scenario violation" value={formatMetric("riskProbability", risk.scenarioProbability)} /><SummaryValue label="Difference" value={formatPercentagePoints(risk.probabilityPointChange)} /><span className="risk-direction">{riskDirection(risk.probabilityPointChange)}</span></div><div className="risk-matrix" role="group" aria-label={`${String(risk.metric)} paired transition counts`}><SummaryValue label="Violation to compliance" value={String(risk.baselineOnlyViolates ?? "Not available")} /><SummaryValue label="Compliance to violation" value={String(risk.scenarioOnlyViolates ?? "Not available")} /><SummaryValue label="Both violate" value={String(risk.bothViolate ?? "Not available")} /><SummaryValue label="Neither violates" value={String(risk.neitherViolates ?? "Not available")} /></div></article>)}</section>)}</div>;
}

function ResourceView({ result, embedded = false }: { result: ComparisonResult; embedded?: boolean }) {
  const baselineResources = asRecords(result.baseline.resourcePoolMetrics);
  return <div className={`resource-view ${embedded ? "embedded" : ""}`}><div className="view-intro"><p className="section-eyebrow">Contextual capacity evidence</p><h3>Resource comparison</h3><p>Higher utilization is not interpreted as automatically better or worse.</p></div>{asRecords(result.scenarios).map((scenario) => { const variantResources = asRecords(asRecord(scenario.variant)?.resourcePoolMetrics); const deltas = asRecord(scenario.resourceUtilizationDeltas); return <section className="resource-scenario" key={String(scenario.scenarioId)}><h3>{String(scenario.scenarioName ?? scenario.scenarioId)}</h3><div className="resource-grid">{baselineResources.map((baselinePool) => { const id = String(baselinePool.resourcePoolId); const scenarioPool = variantResources.find((item) => item.resourcePoolId === id); const baselineMetrics = asRecord(baselinePool.metrics); const scenarioMetrics = asRecord(scenarioPool?.metrics); const delta = asRecord(deltas?.[id]); return <article className="resource-card" key={id}><div className="resource-card-head"><span>Resource pool</span><strong>{humanizeId(id)}</strong></div><dl><ResourceValue label="Baseline utilization" value={formatMetric("resourceUtilization", meanFrom(baselineMetrics, "utilization"))} /><ResourceValue label="Scenario utilization" value={formatMetric("resourceUtilization", meanFrom(scenarioMetrics, "utilization"))} /><ResourceValue label="Utilization delta" value={formatMetric("resourceUtilization", asRecord(delta?.absoluteDelta)?.mean)} /><ResourceValue label="Idle proportion" value={formatMetric("resourceUtilization", meanFrom(scenarioMetrics, "idleCapacityProportion"))} /><ResourceValue label="Mean request wait" value={formatMetric("meanResourceWait", meanFrom(scenarioMetrics, "meanRequestWait"))} /><ResourceValue label="Maximum concurrent usage" value={formatPlain(meanFrom(scenarioMetrics, "maximumConcurrentUsage"))} /><ResourceValue label="Request count" value={formatPlain(meanFrom(scenarioMetrics, "totalRequests"))} /></dl></article>; })}</div></section>; })}</div>;
}

function ResourceValue({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }

function TechnicalView({ result, scenarioDrafts }: { result: ComparisonResult; scenarioDrafts: ScenarioDraft[] }) {
  const representatives = asRecord(result.representatives);
  const objective = String(asRecord(result.objective)?.metric ?? "");
  return <div className="technical-view"><div className="view-intro"><p className="section-eyebrow">Reproducible evidence</p><h3>Technical evidence</h3><p>Hashes, run identities, applied replacements, and integrity remain secondary to the operational comparison.</p></div><dl className="technical-summary"><ResourceValue label="Baseline model hash" value={result.baselineModelHash} /><ResourceValue label="Requested runs" value={String(result.requestedRunCount)} /><ResourceValue label="Confidence level" value={finiteNumber(result.confidenceLevel) === null ? "Not available" : `${Number(result.confidenceLevel) * 100}%`} /><ResourceValue label="Confidence method" value="Normal approximation of the paired mean" /><ResourceValue label="Execution order" value={String(result.execution.executionOrder)} /><ResourceValue label="Ordinary retained events" value={String(result.execution.ordinaryRunRetainedEventCount)} /><ResourceValue label="Work units" value={String(result.workBudget.estimatedWorkUnits)} /><ResourceValue label="Integrity" value={`${result.integrity.status} · ${result.integrity.checksRun} checks`} /></dl>{asRecords(result.scenarios).map((scenario) => { const ranking = rankingFor(result, String(scenario.scenarioId)); const representative = asRecord(asRecord(representatives?.scenario)?.representative); const draft = scenarioDrafts.find((item) => item.id === scenario.scenarioId); const objectiveEvidence = pairedMetric(scenario, objective as MetricKey); return <details className="scenario-technical" key={String(scenario.scenarioId)}><summary>{String(scenario.scenarioName ?? scenario.scenarioId)} · {getScenarioStatus(scenario, ranking)}</summary><dl><ResourceValue label="Intervention" value={draft ? scenarioSummary(draft) : "Not available"} /><ResourceValue label="Materialized hash" value={String(scenario.scenarioModelHash ?? "Not available")} /><ResourceValue label="Paired runs" value={String(scenario.pairedRunCount ?? "Not available")} /><ResourceValue label="Objective mean delta" value={formatMetric(objective as MetricKey, asRecord(objectiveEvidence?.absoluteDelta)?.mean)} /><ResourceValue label="Risk evidence" value={`${asRecords(scenario.riskComparisons).length} configured threshold${asRecords(scenario.riskComparisons).length === 1 ? "" : "s"}`} /><ResourceValue label="Resource evidence" value={`${asRecords(asRecord(scenario.variant)?.resourcePoolMetrics).length} resource pools`} /><ResourceValue label="Guardrail" value={guardrailCopy(scenario)} /><ResourceValue label="Representative seed" value={representative && asRecord(representatives?.scenario)?.variantId === scenario.scenarioId ? String(representative.seed ?? "Not available") : "Not retained for this scenario"} /><ResourceValue label="Integrity" value={result.integrity.status} /></dl><h4>Applied overrides</h4><ul>{asRecords(scenario.appliedOverrides).map((override, index) => <li key={index}>{humanizeId(String(override.entityId))}: {humanizeId(String(override.field))} changed from {String(override.previousValue)} to {String(override.value)}</li>)}</ul></details>; })}<details className="raw-evidence"><summary>Raw comparison result</summary><pre>{JSON.stringify(result, null, 2)}</pre></details></div>;
}

function PrintSummary({ result, baseline, objective }: { result: ComparisonResult; baseline: BaselineForm; objective: string }) {
  return <section className="print-only" aria-label="Printable comparison summary">
    <h2>OpsTwin Scenario Lab comparison</h2>
    <h3>Baseline summary</h3>
    <p>SLA target {baseline.slaTarget} minutes · Level 1 capacity {baseline.level1Capacity} · Level 2 capacity {baseline.level2Capacity}</p>
    <h3>Comparative ranking</h3>
    <table><caption>Backend ranking</caption><thead><tr><th scope="col">Rank</th><th scope="col">Scenario</th><th scope="col">Objective delta</th><th scope="col">Improvement probability</th></tr></thead><tbody>{asRecords(result.ranking).map((ranking) => <tr key={String(ranking.scenarioId)}><td>{String(ranking.rank)}</td><th scope="row">{String(ranking.scenarioId)}</th><td>{formatMetric(objective as MetricKey, ranking.objectiveMeanDelta)}</td><td>{formatMetric("probabilityOfImprovement", ranking.probabilityOfImprovement)}</td></tr>)}</tbody></table>
    <h3>Scenario and risk results</h3>
    {asRecords(result.scenarios).map((scenario) => <div key={String(scenario.scenarioId)}><strong>{String(scenario.scenarioName ?? scenario.scenarioId)}</strong><p>{getScenarioStatus(scenario, rankingFor(result, String(scenario.scenarioId)))} · {guardrailCopy(scenario)} · {String(scenario.pairedRunCount ?? "Not available")} paired runs</p>{asRecords(scenario.riskComparisons).map((risk) => <p key={String(risk.metric)}>{String(risk.metric)}: baseline {formatMetric("riskProbability", risk.baselineProbability)}, scenario {formatMetric("riskProbability", risk.scenarioProbability)}, difference {formatPercentagePoints(risk.probabilityPointChange)}</p>)}</div>)}
    <h3>Execution evidence</h3>
    <p>{result.requestedRunCount} requested paired runs · objective {objective} · integrity {result.integrity.status} ({result.integrity.checksRun} checks)</p>
  </section>;
}

const formatPlain = (value: unknown) => finiteNumber(value) === null ? "Not available" : Number(value).toFixed(2);
const formatPercentagePoints = (value: unknown) => finiteNumber(value) === null ? "Not available" : `${Number(value) >= 0 ? "+" : ""}${(Number(value) * 100).toFixed(1)} percentage points`;
const riskDirection = (value: unknown) => finiteNumber(value) === null ? "Unavailable" : Number(value) < 0 ? "Reduced" : Number(value) > 0 ? "Increased" : "Unchanged";
const formatRiskThreshold = (metric: string, value: unknown) => metric === "slaAttainment" || metric === "terminalFailureRate" ? formatMetric("riskProbability", value) : formatMetric(metric as MetricKey, value);
const humanizeId = (value: string) => value.replaceAll(/[-_.]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
