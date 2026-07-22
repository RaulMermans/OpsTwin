/* eslint-disable @next/next/no-html-link-for-pages -- document-level wordmark */
"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { WorkflowVisualization } from "../../components/workflow/workflow-map";
import { SensitivityPanel } from "../../components/sensitivity/sensitivity-panel";
import { EconomicsPanel } from "../../components/economics/economics-panel";
import { analysisViews, Results, ResourceView, RiskView, TechnicalView, type AnalysisView } from "../../components/results/results-panel";
import { PlaybackPanel } from "../../components/playback/playback-panel";
import { GuidedResultSummary } from "../../components/guided/guided-result-summary";
import { checkSimulationHealth, runScenarioComparison, type ApiError, type ComparisonResult } from "../../lib/api/simulation";
import { buildGuardrail, guardrailOptions, validateGuardrail, type GuardrailDraft, type GuardrailMetric } from "../../lib/scenario-lab/guardrails";
import { guidedEvidenceTargets, guidedEvidenceViews, type GuidedEvidenceView } from "../../lib/scenario-lab/guided-evidence";
import { finiteNumber, guidedMetricLabel, type MetricCategory } from "../../lib/scenario-lab/metrics";
import { asRecord, asRecords, getScenarioStatus, guardrailCopy, rankingFor } from "../../lib/scenario-lab/result-adapter";
import { isLatestRequest } from "../../lib/scenario-lab/request-lifecycle";
import { deleteScenario, duplicateScenario, moveScenario } from "../../lib/scenario-lab/scenario-state";
import { scenarioInputLabels, scenarioLabels, scenarioSummary } from "../../lib/scenario-lab/scenario-labels";
import { buildScenario, estimateWork, validateScenarios, type ScenarioDraft, type ScenarioType } from "../../lib/scenarios/builders";
import { buildBaseline, DEFAULT_FORM, type BaselineForm } from "../../lib/templates/support";

const fields: { key: keyof BaselineForm; label: string; guidedLabel: string; help: string; unit: string; min: number; max: number; step: number }[] = [
  { key: "arrivalInterval", label: "Mean arrival interval", guidedLabel: "Ticket arrival interval", help: "A new ticket arrives every 1.5 minutes on average. Lower values mean heavier demand.", unit: "minutes", min: 0.1, max: 60, step: 0.1 },
  { key: "triageDuration", label: "Triage mean duration", guidedLabel: "Triage duration", help: "Average time used to review and route each incoming ticket.", unit: "minutes", min: 0.1, max: 60, step: 0.1 },
  { key: "level1Capacity", label: "Level 1 capacity", guidedLabel: "Level 1 capacity", help: "Number of Level 1 agents who can handle tickets at the same time.", unit: "agents", min: 1, max: 50, step: 1 },
  { key: "level2Capacity", label: "Level 2 capacity", guidedLabel: "Level 2 capacity", help: "Number of specialist agents who can handle escalated tickets at the same time.", unit: "agents", min: 1, max: 50, step: 1 },
  { key: "qualityDuration", label: "Quality-check duration", guidedLabel: "Quality-check duration", help: "Time required to review a ticket before it is completed.", unit: "minutes", min: 0.1, max: 60, step: 0.1 },
  { key: "escalationProbability", label: "Escalation probability", guidedLabel: "Escalation chance", help: "Percentage of tickets sent to Level 2.", unit: "%", min: 0, max: 100, step: 1 },
  { key: "reworkProbability", label: "Rework probability", guidedLabel: "Rework chance", help: "Percentage of tickets that must be handled again after quality review.", unit: "%", min: 0, max: 100, step: 1 },
  { key: "slaTarget", label: "SLA target", guidedLabel: "Resolution target", help: "Maximum resolution time used to decide whether a ticket met the service target.", unit: "minutes", min: 1, max: 1440, step: 1 },
];

const objectives = { averageCycleTime: "Average cycle time", p95CycleTime: "P95 cycle time", slaAttainment: "SLA attainment", timeWeightedQueueLength: "Queue length" } as const;
type Objective = keyof typeof objectives;
const defaultScenarios: ScenarioDraft[] = [
  { id: "scenario-1", name: "Add one Level 1 agent", type: "level1Staffing", value: 1 },
  { id: "scenario-2", name: "Faster triage", type: "triageProcess", value: 25 },
];

const objectiveDirection = (objective: Objective) => objective === "slaAttainment" ? "maximize" : "minimize";
const scenarioResult = (result: ComparisonResult | null, id: string) => result ? asRecords(result.scenarios).find((item) => item.scenarioId === id) ?? null : null;
const errorTitle = (code: string) => code.toLowerCase().replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());

export function Workspace({ initialMode = "guided" }: { initialMode?: "guided" | "advanced" }) {
  const [mode, setMode] = useState<"guided" | "advanced">(initialMode);
  const [orientationVisible, setOrientationVisible] = useState(true);
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
  const [guidedEvidenceView, setGuidedEvidenceView] = useState<GuidedEvidenceView>("summary");
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
    setGuidedEvidenceView("summary");
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

  function selectGuidedView(view: GuidedEvidenceView, event?: KeyboardEvent<HTMLButtonElement>) {
    if (!event) { setGuidedEvidenceView(view); return; }
    const current = guidedEvidenceViews.findIndex((item) => item.id === view);
    const key = event.key;
    let next = current;
    if (key === "ArrowRight") next = (current + 1) % guidedEvidenceViews.length;
    else if (key === "ArrowLeft") next = (current - 1 + guidedEvidenceViews.length) % guidedEvidenceViews.length;
    else if (key === "Home") next = 0;
    else if (key === "End") next = guidedEvidenceViews.length - 1;
    else return;
    event.preventDefault();
    setGuidedEvidenceView(guidedEvidenceViews[next].id);
    document.getElementById(`guided-tab-${guidedEvidenceViews[next].id}`)?.focus();
  }

  function navigateEvidence(target: string) {
    if (mode === "guided") {
      const view = guidedEvidenceTargets[target];
      if (view) setGuidedEvidenceView(view);
      return;
    }
    if (target === "risk-evidence") { setAnalysisView("risk"); }
    if (target === "technical-evidence") { setAnalysisView("technical"); }
    window.requestAnimationFrame(() => document.getElementById(target)?.scrollIntoView({ block: "start", behavior: "smooth" }));
  }

  return <main className="site-shell workspace-shell">
    <header className="masthead"><a className="wordmark" href="/">OpsTwin</a><span className={`service-status ${health}`}>Simulation service: {health}</span></header>
    <div className="workspace-intro"><div><p className="eyebrow">Scenario Lab · Support operations</p><h1>Compare operating changes with the same simulated conditions.</h1></div><p>Start with a support-operation baseline, compare two changes, then inspect the observed effect and supporting evidence.</p></div>
    <div className="mode-switch" role="group" aria-label="Workspace presentation mode"><button type="button" aria-pressed={mode === "guided"} onClick={() => setMode("guided")}>Guided</button><button type="button" aria-pressed={mode === "advanced"} onClick={() => setMode("advanced")}>Advanced</button></div>
    {orientationVisible && <aside className="orientation" aria-label="First-run orientation"><strong>Start here</strong><ol><li>Review the current operation</li><li>Compare two possible changes</li><li>Read the result and inspect supporting evidence</li></ol><button type="button" className="text-button" onClick={() => setOrientationVisible(false)}>Skip orientation</button></aside>}
    <details className="glossary"><summary>Terminology help</summary><dl><div><dt>Baseline</dt><dd>The current operation used as the reference point.</dd></div><div><dt>Scenario</dt><dd>One possible operating change tested against the baseline.</dd></div><div><dt>Paired comparison</dt><dd>Each change and the baseline use the same simulated conditions for a fairer comparison.</dd></div><div><dt>Objective</dt><dd>The measure used to compare changes.</dd></div><div><dt>Guardrail</dt><dd>A condition a scenario must satisfy to remain eligible.</dd></div><div><dt>Confidence interval</dt><dd>A range describing uncertainty around the estimated average result.</dd></div><div><dt>Improvement probability</dt><dd>The proportion of paired simulations where a scenario performed better for the selected measure.</dd></div><div><dt>Sensitivity</dt><dd>Evidence from varying one assumption across explicit tested values.</dd></div><div><dt>Representative playback</dt><dd>One selected sampled run used to explain timing and flow; it does not represent every run.</dd></div></dl></details>
    <div className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</div>
    <section className="lab-layout" aria-label="Scenario Lab">
      <div className="configuration-column">
        <section className="lab-section baseline-section" aria-labelledby="baseline-title">
          <SectionHeading number="01" eyebrow={mode === "guided" ? "Current operation" : "Immutable reference"} title={mode === "guided" ? "Current operation" : "Baseline"} id="baseline-title" copy="A 100-ticket support workflow. The values below describe what is being tested." />
          {mode === "guided" && <div className="guided-baseline"><ul><li>100 tickets</li><li>1 ticket every {baseline.arrivalInterval} minutes on average</li><li>{baseline.level1Capacity} Level 1 agents</li><li>{baseline.level2Capacity} Level 2 agents</li><li>{baseline.escalationProbability}% escalation chance</li><li>{baseline.reworkProbability}% rework chance</li><li>{baseline.slaTarget}-minute resolution target</li></ul><p>Result to measure: <strong>{guidedMetricLabel(objective, baseline.slaTarget)}</strong><br />Number of matched tests: <strong>{runs}</strong> · Preset: <strong>Standard</strong></p></div>}
          <details open={mode === "advanced"}><summary>{mode === "guided" ? "Review or edit assumptions" : "Baseline assumptions"}</summary><div className="field-grid">{fields.map((field) => {
            const invalid = !Number.isFinite(baseline[field.key]) || baseline[field.key] < field.min || baseline[field.key] > field.max;
            const displayLabel = mode === "guided" ? field.guidedLabel : field.label;
            return <label key={field.key}>{displayLabel}<span className="input-unit"><input aria-label={displayLabel} aria-invalid={invalid} aria-describedby={`${field.key}-hint${invalid ? ` ${field.key}-error` : ""}`} type="number" min={field.min} max={field.max} step={field.step} value={baseline[field.key]} onChange={(event) => { setBaseline({ ...baseline, [field.key]: Number(event.target.value) }); invalidateEvidence(); }} /><small>{field.unit}</small></span><span id={`${field.key}-hint`} className="hint">{mode === "guided" ? field.help : `${field.min}–${field.max} ${field.unit}`}</span>{invalid && <span id={`${field.key}-error`} className="field-error">Enter a value in the documented range.</span>}</label>;
          })}</div></details>
          {baselineError && <p className="inline-error" role="alert">{baselineError.label} must be between {baselineError.min} and {baselineError.max}.</p>}
        </section>

        <section className="lab-section" aria-labelledby="scenario-title">
          <div className="section-heading"><SectionHeading number="02" eyebrow="Two changes" title="What would you like to compare?" id="scenario-title" copy="OpsTwin simulates the same operating conditions for both changes and compares their observed effects." />{mode === "advanced" && <button className="secondary add-scenario" type="button" onClick={() => { setScenarios((items) => items.length >= 3 ? items : [...items, { id: globalThis.crypto?.randomUUID?.() ?? `scenario-${Date.now()}`, name: "Demand change", type: "demand", value: 10 }]); invalidateEvidence(); }} disabled={scenarios.length >= 3}>Add scenario</button>}</div>
          <div className="scenario-list">{scenarios.map((item, index) => {
            const evidence = scenarioResult(result, item.id);
            const ranking = result ? rankingFor(result, item.id) : null;
            const valid = Boolean(item.name.trim()) && Number.isFinite(item.value) && item.value > 0;
            return <article className="scenario-card" key={item.id} data-scenario-index={index} aria-labelledby={`${item.id}-title`}>
              <div className="scenario-card-head"><div><span className={`status-dot ${valid ? "valid" : "invalid"}`}>{valid ? "Ready to compare" : "Needs attention"}</span><h3 id={`${item.id}-title`}>{item.name.trim() || `Scenario ${index + 1}`}</h3><p>{scenarioLabels[item.type]} · 1 override</p></div><span className="scenario-index">{String(index + 1).padStart(2, "0")}</span></div>
              <p className="intervention-summary">{mode === "guided" && item.type === "level1Staffing" ? `Current: ${baseline.level1Capacity} agents · Proposed change: ${baseline.level1Capacity + item.value} agents. Tests whether extra first-line capacity changes waiting time, resolution time, and tickets meeting the target.` : mode === "guided" && item.type === "triageProcess" ? `Current review time: ${baseline.triageDuration} minutes · Proposed change: ${(baseline.triageDuration * (1 - item.value / 100)).toFixed(1)} minutes. Tests whether faster intake review reduces delays further through the process.` : scenarioSummary(item)}</p>
              <details className="scenario-editor" open={mode === "advanced"}><summary>{mode === "guided" ? "Edit scenario" : "Scenario settings"}</summary>
                <label htmlFor={`${item.id}-name`}>Scenario name</label><input id={`${item.id}-name`} aria-invalid={!item.name.trim()} aria-describedby={!item.name.trim() ? `${item.id}-name-error` : undefined} value={item.name} onChange={(event) => updateScenario(item.id, { name: event.target.value })} />{!item.name.trim() && <span className="field-error" id={`${item.id}-name-error`}>Scenario name cannot be empty.</span>}
                <div className="scenario-fields"><label>Scenario type<select value={item.type} onChange={(event) => updateScenario(item.id, { type: event.target.value as ScenarioType })}>{Object.entries(scenarioLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>{scenarioInputLabels[item.type]}<input type="number" min="1" max="100" aria-invalid={!Number.isFinite(item.value) || item.value <= 0} value={item.value} onChange={(event) => updateScenario(item.id, { value: Number(event.target.value) })} /></label></div>
              </details>
              {evidence && <div className="scenario-result-status"><strong>{mode === "guided" && finiteNumber(ranking?.rank) !== null ? "Observed order available in the result" : getScenarioStatus(evidence, ranking)}</strong>{mode === "advanced" && finiteNumber(ranking?.rank) !== null && <span>Rank {String(ranking?.rank)}</span>}<span>{guardrailCopy(evidence)}</span></div>}
              {mode === "advanced" && <div className="scenario-actions" aria-label={`Actions for ${item.name || `scenario ${index + 1}`}`}><button className="text-button scenario-edit" type="button" onClick={() => document.getElementById(`${item.id}-name`)?.focus()}>Edit</button><button className="text-button" type="button" onClick={() => copyScenario(item.id)} disabled={scenarios.length >= 3}>Duplicate</button><button className="text-button" type="button" aria-label={`Move ${item.name || `scenario ${index + 1}`} up`} onClick={() => { setScenarios((items) => moveScenario(items, item.id, -1)); invalidateEvidence(); }} disabled={index === 0}>Move up</button><button className="text-button" type="button" aria-label={`Move ${item.name || `scenario ${index + 1}`} down`} onClick={() => { setScenarios((items) => moveScenario(items, item.id, 1)); invalidateEvidence(); }} disabled={index === scenarios.length - 1}>Move down</button><button className="text-button danger" type="button" onClick={() => removeScenario(item.id, index)}>Delete</button></div>}
            </article>;
          })}</div>
          {scenarioError && <p className="inline-error" role="alert">{scenarioError}</p>}
        </section>

        <section className="lab-section" aria-labelledby="settings-title">
          <SectionHeading number="03" eyebrow={mode === "guided" ? "Comparison settings" : "Shared seed schedule"} title={mode === "guided" ? "How the comparison will run" : "Execution settings"} id="settings-title" copy={mode === "guided" ? "Any required conditions will be checked when the comparison runs." : "Choose the comparison lens and optional operating boundary. The backend evaluates eligibility."} />
          {mode === "guided" && <p className="guided-settings">Result to measure: <strong>{guidedMetricLabel(objective, baseline.slaTarget)}</strong><br />Number of matched tests: <strong>{runs}</strong> · Preset: <strong>Standard</strong></p>}
          <details open={mode === "advanced"}><summary>{mode === "guided" ? "Customize this comparison" : "Advanced comparison settings"}</summary><div className="settings-row"><label>Objective<select value={objective} onChange={(event) => { setObjective(event.target.value as Objective); invalidateEvidence(); }}>{Object.entries(objectives).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Paired runs<select value={runs} onChange={(event) => { setRuns(Number(event.target.value)); invalidateEvidence(); }}>{[10, 25, 50, 100].map((count) => <option key={count}>{count}</option>)}</select></label></div>
          <fieldset className="guardrail-control"><legend>{mode === "guided" ? "Required condition" : "Optional guardrail"}</legend><label className="toggle-row"><input type="checkbox" checked={guardrail.enabled} onChange={(event) => { setGuardrail({ ...guardrail, enabled: event.target.checked }); invalidateEvidence(); }} /><span>{mode === "guided" ? "Check one required condition" : "Evaluate one eligibility guardrail"}</span></label>{guardrail.enabled && <div className="guardrail-fields"><label>Guardrail metric<select value={guardrail.metric} onChange={(event) => { const metric = event.target.value as GuardrailMetric; setGuardrail({ ...guardrail, metric, value: metric === "slaAttainment" || metric === "resourcePoolUtilization" ? 75 : 60, resourcePoolId: metric === "resourcePoolUtilization" ? "level-1-agents" : undefined }); invalidateEvidence(); }}>{Object.entries(guardrailOptions).map(([value, option]) => <option key={value} value={value}>{option.label}</option>)}</select></label>{guardrail.metric === "resourcePoolUtilization" && <label>Resource pool<select value={guardrail.resourcePoolId} onChange={(event) => { setGuardrail({ ...guardrail, resourcePoolId: event.target.value }); invalidateEvidence(); }}><option value="level-1-agents">Level 1 agents</option><option value="level-2-agents">Level 2 agents</option><option value="triage-team">Triage team</option><option value="quality-team">Quality team</option></select></label>}<label>{guardrailOptions[guardrail.metric].label}<span className="input-unit"><input type="number" aria-invalid={Boolean(guardrailError)} aria-describedby={guardrailError ? "guardrail-error" : "guardrail-unit"} min={guardrailOptions[guardrail.metric].minimum} max={guardrailOptions[guardrail.metric].maximum} value={guardrail.value} onChange={(event) => { setGuardrail({ ...guardrail, value: Number(event.target.value) }); invalidateEvidence(); }} /><small id="guardrail-unit">{guardrailOptions[guardrail.metric].unit}</small></span></label></div>}{guardrailError && <p id="guardrail-error" className="inline-error" role="alert">{guardrailError}</p>}{!guardrail.enabled && <p className="guardrail-empty">{mode === "guided" ? "No required conditions added" : "No guardrails configured"}</p>}</fieldset>
          <div className={`work-meter ${work > 30000 ? "over" : ""}`}><span>Estimated work</span><strong>{work.toLocaleString()} / 30,000 item executions</strong></div>{work > 30000 && <p className="inline-error" role="alert">Reduce runs or scenarios to stay within the product work guard.</p>}
          <details><summary>Advanced evidence settings</summary><dl><div><dt>Base seed</dt><dd>20260716</dd></div><div><dt>Confidence</dt><dd>95%</dd></div><div><dt>Representative detail</dt><dd>Sampled · 25 items</dd></div><div><dt>Risk thresholds</dt><dd>80% SLA · baseline SLA target</dd></div></dl></details></details>
        </section>
      </div>

      <aside className="run-panel" aria-labelledby="run-title"><span className="step-number">04</span><p className="panel-kicker">Ready to compare</p><h2 id="run-title">{mode === "guided" ? "Compare two changes with the current operation" : `Baseline vs. ${scenarios.map((item) => item.name).join(" vs. ")}`}</h2><p>{mode === "guided" ? <>OpsTwin creates many simulated versions of the operation using the assumptions shown here. It compares each proposed change under matched conditions. It does not predict exactly what will happen in a real organization.</> : <>Primary measure: {objectives[objective]}. {runs} paired simulations per scenario. Next, you will see the observed result and supporting evidence.</>}</p><button className="primary" type="button" onClick={submit} disabled={state === "running" || health === "unavailable" || Boolean(baselineError || scenarioError || guardrailError) || work > 30000}>{state === "running" ? "Running comparison…" : mode === "guided" ? "Run comparison" : result ? "Run again" : "Run paired comparison"}</button>{state === "running" && <><p className="live-status" aria-live="polite">Running {runs} matched simulated operating days for {scenarios.length} changes.</p><button className="secondary full" type="button" onClick={() => controller.current?.abort()}>Stop waiting</button></>}{error && <div className="error-panel" role="alert" tabIndex={-1} ref={errorRegion}><strong>{errorTitle(error.code)}</strong><p>{error.message}</p><button className="secondary full" type="button" onClick={submit}>Retry comparison</button></div>}<dl className="run-facts"><div><dt>Proposed changes</dt><dd>{scenarios.length} / 3</dd></div><div><dt>{mode === "guided" ? "Matched tests" : "Paired runs"}</dt><dd>{runs}</dd></div><div><dt>{mode === "guided" ? "Result to measure" : "Objective"}</dt><dd>{mode === "guided" ? guidedMetricLabel(objective, baseline.slaTarget) : objectives[objective]}</dd></div></dl></aside>
    </section>
    {mode === "guided" && <section className="guided-evidence" aria-label="Guided evidence" ref={resultRegion} tabIndex={-1}>
      <div className="analysis-tabs guided-evidence-tabs" role="tablist" aria-label="Guided evidence sections">{guidedEvidenceViews.map((item) => <button key={item.id} id={`guided-tab-${item.id}`} type="button" role="tab" aria-selected={guidedEvidenceView === item.id} aria-controls={`guided-panel-${item.id}`} tabIndex={guidedEvidenceView === item.id ? 0 : -1} onClick={() => selectGuidedView(item.id)} onKeyDown={(event) => selectGuidedView(item.id, event)}>{item.label}</button>)}</div>
      <div id="guided-panel-summary" role="tabpanel" aria-labelledby="guided-tab-summary" hidden={guidedEvidenceView !== "summary"}>{result ? <GuidedResultSummary result={result} onNavigate={navigateEvidence} /> : <p className="empty-state">Run the comparison to see the result.</p>}</div>
      <div id="guided-panel-flow" role="tabpanel" aria-labelledby="guided-tab-flow" hidden={guidedEvidenceView !== "flow"}><GuidedPanelIntro copy="See where the proposed change enters the workflow and where waiting or workload changed." /><WorkflowVisualization model={buildBaseline(baseline)} baseline={baseline} scenarios={scenarios} result={result} /></div>
      <div id="guided-panel-risk" role="tabpanel" aria-labelledby="guided-tab-risk" hidden={guidedEvidenceView !== "risk"}><GuidedPanelIntro copy="See how consistently the result appeared across matched simulated operating days." />{result ? <RiskView result={result} /> : <p className="empty-state">Run the comparison first to inspect uncertainty evidence.</p>}</div>
      <div id="guided-panel-resources" role="tabpanel" aria-labelledby="guided-tab-resources" hidden={guidedEvidenceView !== "resources"}><GuidedPanelIntro copy="See which teams were busy, waiting, or constrained." />{result ? <ResourceView result={result} /> : <p className="empty-state">Run the comparison first to inspect team workload.</p>}</div>
      <div id="guided-panel-sensitivity" role="tabpanel" aria-labelledby="guided-tab-sensitivity" hidden={guidedEvidenceView !== "sensitivity"}><GuidedPanelIntro copy="Change one input across explicit values to see whether the result remains similar." /><SensitivityPanel baseline={baseline} health={health} /></div>
      <div id="guided-panel-economics" role="tabpanel" aria-labelledby="guided-tab-economics" hidden={guidedEvidenceView !== "economics"}><GuidedPanelIntro copy="Add only costs you know. OpsTwin will not invent missing values." /><EconomicsPanel baseline={baseline} scenarios={scenarios} runs={runs} objective={objective} health={health} /></div>
      <div id="guided-panel-playback" role="tabpanel" aria-labelledby="guided-tab-playback" hidden={guidedEvidenceView !== "playback"}><GuidedPanelIntro copy="Inspect one selected simulated day to understand timing and flow. It does not represent every run." />{result ? <PlaybackPanel result={result} model={buildBaseline(baseline)} /> : <p className="empty-state">Run a completed comparison first to inspect one selected run.</p>}</div>
      <div id="guided-panel-technical" role="tabpanel" aria-labelledby="guided-tab-technical" hidden={guidedEvidenceView !== "technical"}><GuidedPanelIntro copy="Inspect seeds, contracts, integrity checks, and raw returned evidence." />{result ? <TechnicalView result={result} scenarioDrafts={scenarios} /> : <p className="empty-state">Run the comparison first to inspect technical evidence.</p>}</div>
    </section>}
    {mode === "advanced" && <>
      {result && <><GuidedResultSummary result={result} onNavigate={navigateEvidence} /><Results result={result} baseline={baseline} scenarios={scenarios} settings={{ runs, objective, guardrail }} view={analysisView} setView={selectAnalysisView} metricCategory={metricCategory} setMetricCategory={setMetricCategory} regionRef={resultRegion} /></>}
      <section id="flow-evidence"><WorkflowVisualization model={buildBaseline(baseline)} baseline={baseline} scenarios={scenarios} result={result} /></section>
      <section id="risk-evidence" className="evidence-anchor"><h2>Risk evidence</h2><p>{result ? "Select Risk in the comparison evidence above to inspect paired uncertainty and thresholds." : "Run the comparison first to inspect uncertainty and risk evidence."}</p></section>
      <section id="sensitivity-evidence"><SensitivityPanel baseline={baseline} health={health} /></section>
      <section id="economics-evidence"><EconomicsPanel baseline={baseline} scenarios={scenarios} runs={runs} objective={objective} health={health} /></section>
      <section id="playback-evidence">{result ? <PlaybackPanel result={result} model={buildBaseline(baseline)} /> : <div className="empty-state"><h2>Representative playback</h2><p>Run a completed repeated comparison first to inspect one selected run. Playback does not represent every simulated run.</p></div>}</section>
      <section id="technical-evidence" className="evidence-anchor"><h2>Technical evidence</h2><p>{result ? "Select Technical evidence in the comparison result above to inspect applied overrides, seeds, integrity checks and raw response details." : "Run the comparison first to inspect technical evidence."}</p></section>
    </>}
  </main>;
}

function SectionHeading({ number, eyebrow, title, id, copy }: { number: string; eyebrow: string; title: string; id: string; copy: string }) {
  return <div className="section-title"><span className="step-number">{number}</span><div><p className="section-eyebrow">{eyebrow}</p><h2 id={id}>{title}</h2><p className="section-copy">{copy}</p></div></div>;
}

function GuidedPanelIntro({ copy }: { copy: string }) {
  return <p className="guided-panel-intro">{copy}</p>;
}
