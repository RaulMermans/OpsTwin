import { useEffect, useRef, useState } from "react";
import { invoke, view } from "@forge/bridge";
import { DecisionPanel } from "./decision.jsx";
import { ResultsPanel } from "./results.jsx";
import {
  INTERVENTIONS,
  SECTIONS,
  WINDOW_PRESETS,
  afterCalibrationChange,
  afterConfigChange,
  afterFailedImport,
  afterFinancialChange,
  baselineStatusLabel,
  CSV_TEMPLATE,
  calibrationPayload,
  comparisonPayload,
  defaultAssumptions,
  defaultConfig,
  defaultConstraints,
  defaultImportConfig,
  defaultManualSpec,
  defaultTransform,
  originForSource,
  sourceLinkedCalibrationPayload,
  economicsPayload,
  hybridSupported,
  metricById,
  selectedAlternatives,
  sensitivityPayload,
  transformPayload,
} from "./labState.js";

function metric(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "unavailable";
  return Number(value).toFixed(3);
}

function qualityLine(item) {
  const measured = item.value === null || item.value === undefined ? "n/a" : Number(item.value).toFixed(3);
  return `${item.metricId}: ${item.status} (${measured}) — ${item.explanation}`;
}

function newRequestId() {
  return `req-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

export function App() {
  const [section, setSection] = useState("overview");
  const [phase, setPhase] = useState("initial");
  const [identity, setIdentity] = useState(null);
  const [project, setProject] = useState(null);
  const [requestTypes, setRequestTypes] = useState(null);
  const [config, setConfig] = useState(defaultConfig());
  const [importConfig, setImportConfig] = useState(defaultImportConfig());
  const [run, setRun] = useState({ status: "ready", evidence: null, message: null, remoteStatus: "not checked" });
  const [calibration, setCalibration] = useState({
    status: "ready",
    evidence: null,
    message: null,
    fixtureId: "cg5-hybrid-support",
    approveLabAssumptions: false,
    sourceMode: "synthetic",
  });
  const [transform, setTransform] = useState(defaultTransform());
  const [experiment, setExperiment] = useState({ status: "ready", evidence: null, message: null, requestId: null });
  const [sensitivity, setSensitivity] = useState({ status: "ready", evidence: null, message: null, requestId: null });
  const [assumptions, setAssumptions] = useState(defaultAssumptions());
  const [constraints, setConstraints] = useState(defaultConstraints());
  const [exploreParameter, setExploreParameter] = useState("aiSubscriptionMonthly");
  const [exploreStrategy, setExploreStrategy] = useState("hybrid");
  const [economics, setEconomics] = useState({ status: "ready", evidence: null, message: null, requestId: null });
  const [sourceMode, setSourceMode] = useState("synthetic");
  const [manualSpec, setManualSpec] = useState(defaultManualSpec());
  const [csvText, setCsvText] = useState("");
  const [jiraStaffing, setJiraStaffing] = useState({
    triageCapacity: 2,
    resolutionCapacity: 3,
    triageMeanMinutes: 8,
    resolutionMeanMinutes: 20,
  });
  const [mappingReviewed, setMappingReviewed] = useState(false);
  const [statusMapping, setStatusMapping] = useState([]);
  const calibrating = useRef(false);
  const experimenting = useRef(false);
  const [importState, setImportState] = useState({
    status: "none",
    snapshot: null,
    message: null,
    stale: false,
    mode: null,
  });
  const running = useRef(false);
  const importing = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setPhase("loading-project");
    Promise.all([invoke("getLabIdentity"), invoke("getProjectSnapshot"), invoke("getRequestTypes"), view.getContext()])
      .then(([lab, snapshot, types, context]) => {
        if (cancelled) return;
        setIdentity({ ...lab, moduleType: context?.extension?.type ?? null });
        setProject(snapshot);
        setRequestTypes(types);
        if (snapshot?.kind === "untrusted_project" || snapshot?.kind === "missing_context") {
          setPhase("project-denied");
          return;
        }
        if (snapshot?.classification === "permission_denied" || snapshot?.classification === "authentication_failed") {
          setPhase("project-denied");
          return;
        }
        if (snapshot?.classification === "ok") {
          setPhase("ready");
          return;
        }
        setPhase("project-denied");
      })
      .catch((caught) => {
        if (!cancelled) {
          setPhase("failed");
          setRun((current) => ({
            ...current,
            status: "failed",
            message: caught instanceof Error ? caught.message : "The lab could not load project context.",
          }));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function updateConfig(patch) {
    setConfig((current) => {
      const next = { ...current, ...patch };
      setRun((previous) => afterConfigChange(previous));
      return next;
    });
  }

  async function runComparison() {
    if (running.current || phase !== "ready") return;
    running.current = true;
    setRun({ status: "running", evidence: null, message: null, remoteStatus: "invoking" });
    try {
      const result = await invoke("runSyntheticComparison", comparisonPayload(config));
      if (result?.status === "ok" && result.evidence) {
        setRun({
          status: "completed",
          evidence: result.evidence,
          message: null,
          remoteStatus: "authenticated",
        });
      } else if (result?.classification === "timeout") {
        setRun({ status: "timeout", evidence: null, message: result.message, remoteStatus: "failed" });
      } else if (result?.kind === "untrusted_project" || result?.kind === "missing_context") {
        setPhase("project-denied");
        setRun({ status: "failed", evidence: null, message: result.message, remoteStatus: "blocked" });
      } else {
        setRun({
          status: "failed",
          evidence: null,
          message: result?.message ?? "The comparison could not be completed.",
          remoteStatus: "failed",
        });
      }
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "The comparison could not be completed.";
      const timeout = /timed out/i.test(message);
      setRun({
        status: timeout ? "timeout" : "failed",
        evidence: null,
        message,
        remoteStatus: "failed",
      });
    } finally {
      running.current = false;
    }
  }

  async function runImport() {
    if (importing.current || phase !== "ready") return;
    importing.current = true;
    const previous = importState.snapshot;
    setImportState({ status: "running", snapshot: null, message: null, stale: false, mode: "live", stage: "starting" });
    try {
      const result = await invoke("importOperationalSnapshot", { windowDays: importConfig.windowDays });
      if (result?.kind === "untrusted_project" || result?.kind === "missing_context") {
        setPhase("project-denied");
        setImportState({ status: "failed", ...afterFailedImport(previous), message: result.message, mode: "live" });
      } else if (result?.status === "completed" || result?.status === "partial") {
        setImportState({
          status: result.status,
          snapshot: result.snapshot,
          message: result.status === "partial" ? "Import finished with incomplete extraction." : null,
          stale: false,
          mode: "live",
          stage: result.stage,
        });
      } else {
        setImportState({
          status: result?.classification === "rate_limited" ? "rate_limited" : result?.classification === "timeout" ? "timeout" : "failed",
          ...afterFailedImport(previous),
          message: result?.message ?? "Import failed.",
          mode: "live",
        });
      }
    } catch (caught) {
      setImportState({
        status: "failed",
        ...afterFailedImport(previous),
        message: caught instanceof Error ? caught.message : "Import failed.",
        mode: "live",
      });
    } finally {
      importing.current = false;
    }
  }

  async function runSyntheticDemo() {
    if (importing.current || phase !== "ready") return;
    importing.current = true;
    setImportState({ status: "running", snapshot: null, message: null, stale: false, mode: "synthetic-demo" });
    try {
      const result = await invoke("loadSyntheticOperationalDemo", { profile: "golden" });
      if (result?.status === "completed" && result.snapshot) {
        setImportState({
          status: "completed",
          snapshot: result.snapshot,
          message: "Synthetic demonstration data. Not this Jira project's history.",
          stale: false,
          mode: "synthetic-demo",
        });
      } else {
        setImportState({ status: "failed", snapshot: null, stale: false, message: result?.message ?? "Synthetic demo failed.", mode: "synthetic-demo" });
      }
    } catch (caught) {
      setImportState({
        status: "failed",
        snapshot: null,
        stale: false,
        message: caught instanceof Error ? caught.message : "Synthetic demo failed.",
        mode: "synthetic-demo",
      });
    } finally {
      importing.current = false;
    }
  }

  function applyBaselineResult(result, mode) {
    if (result?.status === "review_required" || result?.kind === "missing_principal") {
      setCalibration((current) => ({
        ...current,
        status: result.status === "review_required" ? "preview" : "failed",
        message: result.message,
      }));
      if (result.status === "review_required") setMappingReviewed(false);
      return;
    }
    if (result?.status === "ok" && result.evidence) {
      setCalibration((current) => ({
        ...current,
        status: result.evidence.constructedModel ? "completed" : "preview",
        evidence: result.evidence,
        sourceMode: mode,
        message: result.evidence.disclosure,
      }));
      if (!result.evidence.constructedModel && Array.isArray(result.evidence.suggestedMapping?.statuses)) {
        setStatusMapping(result.evidence.suggestedMapping.statuses);
        setMappingReviewed(false);
      }
      if (result.evidence.constructedModel) {
        setAssumptions((current) => ({
          ...current,
          origin: originForSource(mode),
          baselineTriageFte: result.evidence.baselineInventory?.triageCapacity ?? current.baselineTriageFte,
          baselineResolutionFte: result.evidence.baselineInventory?.resolutionCapacity ?? current.baselineResolutionFte,
        }));
        setExperiment({ status: "ready", evidence: null, message: "Baseline changed. Previous experiment results are stale.", requestId: null });
        setEconomics({ status: "ready", evidence: null, message: null, requestId: null });
      }
      return;
    }
    setCalibration((current) => ({
      ...current,
      status: "failed",
      evidence: current.evidence,
      message: result?.message ?? "Baseline construction failed.",
    }));
  }

  async function runCalibration() {
    if (calibrating.current || phase !== "ready") return;
    calibrating.current = true;
    setCalibration((current) => ({ ...current, status: "running", message: null, sourceMode: "synthetic" }));
    try {
      const result = await invoke("constructBaseline", {
        ...calibrationPayload(calibration.fixtureId, calibration.approveLabAssumptions),
        sourceMode: "synthetic",
      });
      applyBaselineResult(result, "synthetic");
    } catch (caught) {
      setCalibration((current) => ({
        ...current,
        status: "failed",
        evidence: null,
        message: caught instanceof Error ? caught.message : "Synthetic calibration failed.",
      }));
    } finally {
      calibrating.current = false;
    }
  }

  async function runManualBaseline() {
    if (calibrating.current || phase !== "ready") return;
    calibrating.current = true;
    setCalibration((current) => ({ ...current, status: "running", message: null, sourceMode: "manual" }));
    try {
      const result = await invoke("constructBaseline", { sourceMode: "manual", manual: manualSpec });
      applyBaselineResult(result, "manual");
    } catch (caught) {
      setCalibration((current) => ({
        ...current,
        status: "failed",
        evidence: null,
        message: caught instanceof Error ? caught.message : "Manual baseline failed.",
      }));
    } finally {
      calibrating.current = false;
    }
  }

  async function runJiraBaseline(construct) {
    if (calibrating.current || phase !== "ready") return;
    if (!importState.snapshot || importState.mode === "synthetic-demo") {
      setCalibration((current) => ({
        ...current,
        status: "failed",
        message: "Import authorized Jira records first. Synthetic demonstration data is not substituted.",
      }));
      return;
    }
    calibrating.current = true;
    setCalibration((current) => ({ ...current, status: "running", message: null, sourceMode: "jira" }));
    try {
      const result = await invoke("constructBaseline", {
        sourceMode: "jira",
        windowDays: importState.snapshot.importConfiguration?.windowDays ?? importConfig.windowDays,
        observationWindow: {
          ...importState.snapshot.observationWindow,
          windowDays: importState.snapshot.importConfiguration?.windowDays ?? importConfig.windowDays,
        },
        calibration: construct
          ? sourceLinkedCalibrationPayload(calibration.evidence, jiraStaffing, mappingReviewed, statusMapping)
          : undefined,
      });
      applyBaselineResult(result, "jira");
    } catch (caught) {
      setCalibration((current) => ({
        ...current,
        status: "failed",
        message: caught instanceof Error ? caught.message : "Source-linked baseline failed.",
      }));
    } finally {
      calibrating.current = false;
    }
  }

  async function runCsvBaseline(construct) {
    if (calibrating.current || phase !== "ready") return;
    calibrating.current = true;
    setCalibration((current) => ({ ...current, status: "running", message: null, sourceMode: "csv" }));
    try {
      const result = await invoke("constructBaseline", {
        sourceMode: "csv",
        csvText,
        calibration: construct
          ? sourceLinkedCalibrationPayload(calibration.evidence, jiraStaffing, mappingReviewed, statusMapping)
          : undefined,
      });
      applyBaselineResult(result, "csv");
    } catch (caught) {
      setCalibration((current) => ({
        ...current,
        status: "failed",
        message: caught instanceof Error ? caught.message : "CSV baseline failed.",
      }));
    } finally {
      calibrating.current = false;
    }
  }

  function updateTransform(patch) {
    setTransform((current) => ({ ...current, ...patch }));
    setExperiment((previous) =>
      previous.evidence
        ? { status: "stale", evidence: previous.evidence, message: "Results are stale because the configuration changed.", requestId: previous.requestId }
        : previous,
    );
    setEconomics((previous) =>
      previous.evidence
        ? { ...previous, status: "stale", message: "Economic results are stale because operational inputs changed." }
        : previous,
    );
  }

  function updateAssumptions(patch) {
    setAssumptions((current) => ({ ...current, ...patch }));
    setEconomics((previous) => afterFinancialChange(previous));
  }

  function updateConstraints(patch) {
    setConstraints((current) => ({ ...current, ...patch }));
    setEconomics((previous) => afterFinancialChange(previous));
  }

  async function runExperiment() {
    if (experimenting.current || phase !== "ready") return;
    if (!calibration.evidence?.constructedModel) {
      setExperiment({
        status: "invalid",
        evidence: null,
        message: "Construct a baseline first. Interventions are not run against structurally invalid models.",
        requestId: null,
      });
      return;
    }
    const alternatives = selectedAlternatives(transform, calibration);
    if (alternatives.length === 0) {
      setExperiment({
        status: "invalid",
        evidence: null,
        message: "Select at least one compatible alternative.",
        requestId: null,
      });
      return;
    }
    const requestId = newRequestId();
    experimenting.current = true;
    setExperiment({ status: "running", evidence: null, message: null, requestId });
    try {
      const result = await invoke("runTransformationExperiment", transformPayload(calibration, transform, requestId));
      setExperiment((current) => {
        if (current.requestId !== requestId) {
          return current;
        }
        if (result?.status === "ok" && result.evidence) {
          return {
            status:
              result.evidence.experimentStatus === "complete"
                ? "completed"
                : result.evidence.experimentStatus,
            evidence: result.evidence,
            message: result.evidence.disclosure,
            requestId,
          };
        }
        return {
          status: result?.classification === "timeout" ? "timeout" : "failed",
          evidence: null,
          message: result?.message ?? "The transformation experiment failed.",
          requestId,
        };
      });
      if (result?.status === "ok") {
        setEconomics({ status: "ready", evidence: null, message: "Operational evidence updated. Evaluate investment to refresh economics.", requestId: null });
        setSection("results");
      }
    } catch (caught) {
      setExperiment((current) =>
        current.requestId !== requestId
          ? current
          : {
              status: /timed out/i.test(String(caught)) ? "timeout" : "failed",
              evidence: null,
              message: caught instanceof Error ? caught.message : "The transformation experiment failed.",
              requestId,
            },
      );
    } finally {
      experimenting.current = false;
    }
  }

  async function runSensitivity() {
    if (experimenting.current || phase !== "ready" || !calibration.evidence?.constructedModel) return;
    if (transform.sensitivityParameter === "autoCompleteFraction" && !hybridSupported(calibration)) {
      setSensitivity({
        status: "invalid",
        evidence: null,
        message: "This baseline does not support automated resolution. Select the hybrid-capable transformation baseline.",
        requestId: null,
      });
      return;
    }
    const requestId = newRequestId();
    experimenting.current = true;
    setSensitivity({ status: "running", evidence: null, message: null, requestId });
    try {
      const result = await invoke("runTransformationExperiment", sensitivityPayload(calibration, transform, requestId));
      setSensitivity((current) => {
        if (current.requestId !== requestId) return current;
        if (result?.status === "ok" && result.evidence) {
          return { status: "completed", evidence: result.evidence, message: null, requestId };
        }
        return { status: "failed", evidence: null, message: result?.message ?? "Sensitivity run failed.", requestId };
      });
    } catch (caught) {
      setSensitivity((current) =>
        current.requestId !== requestId
          ? current
          : { status: "failed", evidence: null, message: caught instanceof Error ? caught.message : "Sensitivity run failed.", requestId },
      );
    } finally {
      experimenting.current = false;
    }
  }

  async function runEconomics(explore) {
    if (experimenting.current || phase !== "ready") return;
    if (!experiment.evidence || experiment.status === "stale" || experiment.status === "failed") {
      setEconomics({
        status: "invalid",
        evidence: economics.evidence,
        message: "Run a current transformation experiment before economic evaluation.",
        requestId: economics.requestId,
      });
      return;
    }
    if (experiment.evidence.experimentStatus === "failed") {
      setEconomics({
        status: "failed",
        evidence: null,
        message: "A failed experiment cannot produce an economic comparison.",
        requestId: null,
      });
      return;
    }
    const requestId = newRequestId();
    experimenting.current = true;
    setEconomics({ status: "running", evidence: economics.evidence, message: null, requestId });
    try {
      const result = await invoke(
        "runEconomicEvaluation",
        economicsPayload(calibration, transform, experiment, assumptions, constraints, requestId, explore),
      );
      setEconomics((current) => {
        if (current.requestId !== requestId) return current;
        if (result?.status === "ok" && result.evidence) {
          return { status: "completed", evidence: result.evidence, message: null, requestId };
        }
        return {
          status: "failed",
          evidence: current.evidence,
          message: result?.message ?? "The economic evaluation failed.",
          requestId,
        };
      });
    } catch (caught) {
      setEconomics((current) =>
        current.requestId !== requestId
          ? current
          : {
              status: "failed",
              evidence: current.evidence,
              message: caught instanceof Error ? caught.message : "The economic evaluation failed.",
              requestId,
            },
      );
    } finally {
      experimenting.current = false;
    }
  }

  const intervention = INTERVENTIONS[config.intervention];
  const projectOk = project?.classification === "ok";
  const jiraStatus = projectOk ? "connected" : phase === "loading-project" ? "checking" : "blocked";
  const parameterValue =
    config.intervention === "add-capacity" ? config.extraCapacity : config.triageReductionPercent;
  const snapshot = importState.snapshot;
  const cases = metricById(snapshot, "observed_case_count");
  const cycle = metricById(snapshot, "cycle_time_minutes");
  const liveEmpty = importState.status === "completed" && snapshot?.completenessStatus === "empty";
  const hybridOk = hybridSupported(calibration);
  const nextAction =
    phase !== "ready"
      ? "Resolve project access."
      : !calibration.evidence?.constructedModel
        ? "Choose a data source, construct a baseline, and review assumptions."
        : experiment.status !== "completed" && experiment.status !== "partial"
          ? "Configure alternatives in Transformation Lab and run the comparison."
          : economics.status === "completed"
            ? "Review the Investment Decision workspace."
            : "Inspect Results & Evidence, then evaluate investment assumptions.";

  return (
    <main className="lab">
      <p className="eyebrow">Development integration — CG-7</p>
      <h1>OpsTwin for Jira</h1>
      <h2>AI Transformation Lab — Simulate before you automate</h2>
      <p>
        Bring your own operation, compare human and AI strategies, and evaluate financial consequences before automating.
        User-defined models are exploratory unless independent historical validation is shown.
      </p>

      <nav className="sections" aria-label="Product sections">
        {SECTIONS.map((item) => (
          <button key={item.id} type="button" onClick={() => setSection(item.id)} aria-current={section === item.id}>
            {item.label}
          </button>
        ))}
      </nav>

      {phase === "loading-project" ? <p>Loading project…</p> : null}
      {phase === "project-denied" ? <p className="alert" role="alert">{project?.message ?? "This user cannot access the current project."}</p> : null}
      {phase === "failed" ? <p className="alert" role="alert">{run.message}</p> : null}

      {section === "overview" ? (
        <section>
          <div className="grid">
            <div className="card">
              <strong>Project</strong>
              {projectOk ? `${project.name} (${project.projectKey})` : identity?.projectKey ?? "not provided"}
            </div>
            <div className="card">
              <strong>Jira connection</strong>
              {jiraStatus}
            </div>
            <div className="card">
              <strong>Operational snapshot</strong>
              {importState.status === "none"
                ? "no live import"
                : `${importState.status}${importState.mode === "synthetic-demo" ? " (synthetic demonstration)" : ""}`}
            </div>
            <div className="card">
              <strong>Source</strong>
              {calibration.sourceMode ?? sourceMode}
            </div>
            <div className="card">
              <strong>Baseline</strong>
              {baselineStatusLabel(calibration.evidence)}
            </div>
            <div className="card">
              <strong>Latest experiment</strong>
              {experiment.status === "completed" || experiment.status === "partial" ? experiment.status : "none in this session"}
            </div>
          </div>
          {importState.mode !== "synthetic-demo" && snapshot && !liveEmpty ? (
            <dl>
              <dt>Cases observed</dt>
              <dd>{cases?.value ?? snapshot.cases.length}</dd>
              <dt>Cycle time p50 (minutes)</dt>
              <dd>{cycle?.value?.p50 ?? "unavailable"}</dd>
              <dt>Open at window end</dt>
              <dd>{metricById(snapshot, "open_cases_at_window_end")?.value ?? "unavailable"}</dd>
              <dt>Resolved</dt>
              <dd>{metricById(snapshot, "resolution_count")?.value ?? "unavailable"}</dd>
            </dl>
          ) : (
            <p className="banner">
              {liveEmpty
                ? "The authorized query succeeded and observed no cases. Synthetic numbers are not substituted into this overview."
                : "No live operational history is shown here. Use Operational Data to import OPS records, or construct a synthetic demonstration baseline."}
            </p>
          )}
          {(snapshot?.dataQuality ?? []).filter((item) => item.status === "fail" || item.status === "warning").length ? (
            <div className="status">
              {(snapshot.dataQuality ?? [])
                .filter((item) => item.status === "fail" || item.status === "warning")
                .map((item) => (
                  <p key={item.metricId}>{qualityLine(item)}</p>
                ))}
            </div>
          ) : null}
          <div className="grid">
            {[
              ["jira", "Connect Jira data", "Import the current project"],
              ["manual", "Build your own operation", "Configure demand and staffing"],
              ["csv", "Upload a dataset", "CSV event log template"],
              ["synthetic", "Explore a demonstration", "Server-controlled synthetic fixture"],
            ].map(([id, title, detail]) => (
              <button
                key={id}
                type="button"
                className="card"
                onClick={() => {
                  setSourceMode(id);
                  setSection(id === "manual" || id === "synthetic" ? "baseline" : "data");
                }}
              >
                <strong>{title}</strong>
                {detail}
              </button>
            ))}
          </div>
          <p className="next">
            <strong>Next:</strong> {nextAction}
          </p>
          <button className="primary" type="button" onClick={() => setSection(!calibration.evidence?.constructedModel ? "baseline" : "lab")}>
            Continue
          </button>
        </section>
      ) : null}

      {section === "data" && phase === "ready" ? (
        <section>
          <h3>Source</h3>
          <p>
            Connected project {project?.name} ({project?.projectKey}). Service desk{" "}
            {requestTypes?.serviceDeskId ?? "not visible"}. Authorization follows the signed-in Jira user.
          </p>
          <p>Read-only import of issue metadata, changelogs, worklogs, and SLA cycles. Descriptions, comments, and attachments are not retrieved. Missing values are not shown as zero. Status residence is not processing time. Assignee counts are not staffing capacity.</p>
          <label className="stack">
            Observation window
            <select
              value={importConfig.windowDays}
              onChange={(event) => setImportConfig({ windowDays: Number(event.target.value) })}
              disabled={importState.status === "running"}
            >
              {WINDOW_PRESETS.map((days) => (
                <option key={days} value={days}>
                  Last {days} days
                </option>
              ))}
            </select>
          </label>
          <button className="primary" type="button" onClick={runImport} disabled={importState.status === "running"}>
            {importState.status === "running" ? "Importing…" : "Import operational records"}
          </button>
          <p className="banner">
            CSV and Jira imports stay minimized: no descriptions, comments, attachments, or personal names are sent to the simulation remote.
          </p>
          <label className="stack">
            CSV event log
            <textarea rows="6" value={csvText} onChange={(event) => setCsvText(event.target.value)} placeholder="Paste the supported CSV template" />
          </label>
          <button
            className="secondary"
            type="button"
            onClick={() => {
              const blob = new Blob([CSV_TEMPLATE], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = "opstwin-event-log-template.csv";
              link.click();
              URL.revokeObjectURL(url);
            }}
          >
            Download CSV template
          </button>
          <button className="secondary" type="button" onClick={() => navigator.clipboard?.writeText(CSV_TEMPLATE)}>
            Copy CSV template
          </button>
          <button className="secondary" type="button" onClick={() => runCsvBaseline(false)} disabled={calibration.status === "running"}>
            Validate CSV
          </button>
          <button className="secondary" type="button" onClick={runSyntheticDemo} disabled={importState.status === "running"}>
            Load synthetic demonstration data
          </button>
          {importState.status === "running" ? <p>Import in progress{importState.stage ? `: ${importState.stage}` : ""}.</p> : null}
          {importState.status === "failed" || importState.status === "rate_limited" || importState.status === "timeout" ? (
            <p className="alert" role="alert">
              {importState.status}: {importState.message}
              {importState.stale ? " The previous snapshot is not shown as current." : ""}
            </p>
          ) : null}
          {snapshot ? (
            <>
              {importState.mode === "synthetic-demo" ? (
                <p className="status" role="status">Synthetic demonstration. These records are not this project&apos;s live history.</p>
              ) : null}
              {snapshot.completenessStatus === "empty" ? <p>Valid empty dataset: the query succeeded and observed no cases.</p> : null}
              {importState.status === "partial" ? <p className="status" role="status">Partial import. Extraction was truncated. This is not a complete dataset.</p> : null}
              <h3>Descriptive evidence</h3>
              <dl>
                <dt>Cases observed</dt>
                <dd>{cases?.value ?? snapshot.cases.length}</dd>
                <dt>Lifecycle events</dt>
                <dd>{snapshot.events.length}</dd>
                <dt>Observation window</dt>
                <dd>
                  {snapshot.observationWindow.start} → {snapshot.observationWindow.end}
                </dd>
                <dt>Request-type mix</dt>
                <dd>{JSON.stringify(metricById(snapshot, "request_type_distribution")?.value ?? [])}</dd>
                <dt>Cycle time (p50 minutes)</dt>
                <dd>{cycle?.value?.p50 ?? "unavailable"}</dd>
                <dt>Open at window end</dt>
                <dd>{metricById(snapshot, "open_cases_at_window_end")?.value ?? "unavailable"}</dd>
                <dt>Resolved</dt>
                <dd>{metricById(snapshot, "resolution_count")?.value ?? "unavailable"}</dd>
                <dt>Worklog coverage</dt>
                <dd>{snapshot.extraction?.worklogCompleteness ?? "unavailable"}</dd>
                <dt>SLA evidence</dt>
                <dd>{snapshot.extraction?.slaCompleteness ?? "unavailable"}</dd>
              </dl>
              <h3>Data quality</h3>
              <ul>
                {snapshot.dataQuality.map((item) => (
                  <li key={item.metricId}>{qualityLine(item)}</li>
                ))}
              </ul>
              <p>{snapshot.limitations.join(" ")}</p>
              {snapshot.readiness === "insufficient_for_calibration" ? (
                <p>Evidence is insufficient for calibration: required process observations are missing or incomplete, so parameters cannot be estimated from this snapshot.</p>
              ) : null}
              <p className="banner">
                Live Jira records are minimized before remote calibration. Status residence is not processing time. A successful import is not historical validation.
              </p>
              <button className="primary" type="button" onClick={() => runJiraBaseline(false)} disabled={calibration.status === "running"}>
                Inspect source-linked mapping
              </button>
            </>
          ) : (
            <p>No data imported.</p>
          )}
        </section>
      ) : null}

      {section === "baseline" && phase === "ready" ? (
        <section>
          <h3>Choose how to build the baseline</h3>
          <p role="status">
            Every source uses the same support-triage-resolution model. Manual and imported operations are labeled
            exploratory unless holdout validation passes.
          </p>
          <h3>Build your own operation</h3>
          <div className="grid">
            {[
              ["expectedVolume", "Expected requests"],
              ["observationDays", "Observation days"],
              ["operatingHoursPerDay", "Operating hours / day"],
              ["triageCapacity", "Triage staff"],
              ["resolutionCapacity", "Resolution staff"],
              ["triageMeanMinutes", "Triage minutes"],
              ["resolutionMeanMinutes", "Resolution minutes"],
              ["triageToResolutionProbability", "P(triage → resolution)"],
              ["slaMinutes", "SLA minutes"],
            ].map(([key, label]) => (
              <label key={key} className="stack">
                {label}
                <input
                  type="number"
                  step="any"
                  value={manualSpec[key]}
                  onChange={(event) => setManualSpec((current) => ({ ...current, [key]: Number(event.target.value) }))}
                />
              </label>
            ))}
          </div>
          <button className="primary" type="button" onClick={runManualBaseline} disabled={calibration.status === "running"}>
            Construct user-defined baseline
          </button>
          {calibration.sourceMode === "jira" || calibration.sourceMode === "csv" || calibration.evidence?.suggestedMapping ? (
            <>
              <h3>Source-linked assumptions</h3>
              <p>Capacity and processing times are not inferred from assignees or status residence.</p>
              <div className="grid">
                {[
                  ["triageCapacity", "Triage staff"],
                  ["resolutionCapacity", "Resolution staff"],
                  ["triageMeanMinutes", "Triage minutes"],
                  ["resolutionMeanMinutes", "Resolution minutes"],
                ].map(([key, label]) => (
                  <label key={key} className="stack">
                    {label}
                    <input
                      type="number"
                      value={jiraStaffing[key]}
                      onChange={(event) => setJiraStaffing((current) => ({ ...current, [key]: Number(event.target.value) }))}
                    />
                  </label>
                ))}
              </div>
              <h3>Operational mapping</h3>
              <p>Suggested mappings are not approved facts. Status residence is not processing time.</p>
              {(statusMapping.length ? statusMapping : calibration.evidence?.suggestedMapping?.statuses ?? []).map((item) => (
                <div className="grid" key={item.statusId}>
                  <span>{item.displayName || item.statusId}</span>
                  <label className="stack">
                    Role
                    <select
                      value={item.role}
                      onChange={(event) => {
                        const role = event.target.value;
                        setStatusMapping((current) => {
                          const base = current.length ? current : calibration.evidence?.suggestedMapping?.statuses ?? [];
                          return base.map((row) =>
                            row.statusId === item.statusId
                              ? {
                                  ...row,
                                  role,
                                  stageId: role === "processing" ? row.stageId || "triage" : null,
                                  reviewed: false,
                                }
                              : row,
                          );
                        });
                        setMappingReviewed(false);
                        setExperiment((previous) =>
                          previous.evidence
                            ? { status: "stale", evidence: previous.evidence, message: "Mapping changed. Previous results are stale.", requestId: previous.requestId }
                            : previous,
                        );
                        setEconomics((previous) =>
                          previous.evidence
                            ? { ...previous, status: "stale", message: "Mapping changed. Reconstruct the baseline before using financial results." }
                            : previous,
                        );
                        setCalibration((current) =>
                          current.evidence?.constructedModel
                            ? { ...current, status: "preview", message: "Mapping changed. Construct the baseline again." }
                            : current,
                        );
                      }}
                    >
                      <option value="queue">Waiting</option>
                      <option value="processing">Processing</option>
                      <option value="completed">Completed</option>
                      <option value="excluded">Excluded</option>
                      <option value="unknown">Unknown</option>
                    </select>
                  </label>
                  {item.role === "processing" ? (
                    <label className="stack">
                      Stage
                      <select
                        value={item.stageId || "triage"}
                        onChange={(event) => {
                          const stageId = event.target.value;
                          setStatusMapping((current) => {
                            const base = current.length ? current : calibration.evidence?.suggestedMapping?.statuses ?? [];
                            return base.map((row) => (row.statusId === item.statusId ? { ...row, stageId, reviewed: false } : row));
                          });
                          setMappingReviewed(false);
                        }}
                      >
                        <option value="triage">Triage processing</option>
                        <option value="resolution">Resolution processing</option>
                      </select>
                    </label>
                  ) : null}
                </div>
              ))}
              <label className="inline">
                <input type="checkbox" checked={mappingReviewed} onChange={(event) => setMappingReviewed(event.target.checked)} />
                I reviewed the operational mapping. Status residence is not processing time.
              </label>
              <button className="primary" type="button" onClick={() => (calibration.sourceMode === "csv" ? runCsvBaseline(true) : runJiraBaseline(true))} disabled={calibration.status === "running" || !mappingReviewed}>
                Construct source-linked baseline
              </button>
            </>
          ) : null}
          <h3>Demonstration fixture</h3>
          <label className="stack">
            Synthetic demonstration baseline
            <select
              value={calibration.fixtureId}
              onChange={(event) => {
                setCalibration((current) => afterCalibrationChange({ ...current, fixtureId: event.target.value }));
                setExperiment({ status: "ready", evidence: null, message: "Calibration changed. Previous experiment results are stale.", requestId: null });
              }}
              disabled={calibration.status === "running"}
            >
              <option value="cg5-hybrid-support">Hybrid-capable support operation (synthetic)</option>
              <option value="cg3-golden-analytical">Golden analytical (synthetic, no auto-complete route)</option>
              <option value="cg3-partially-observable">Partially observable (assumptions required)</option>
            </select>
          </label>
          <p>
            {calibration.fixtureId === "cg5-hybrid-support"
              ? "This template includes an existing triage route to both resolution and completion, so hybrid automation can shift that route."
              : calibration.fixtureId === "cg3-golden-analytical"
                ? "Golden routing completes only through resolution. Hybrid automation is structurally unavailable."
                : "This fixture cannot construct a model until laboratory assumptions are explicitly accepted."}
          </p>
          <label className="inline">
            <input
              type="checkbox"
              checked={calibration.approveLabAssumptions}
              onChange={(event) => {
                setCalibration((current) =>
                  afterCalibrationChange({ ...current, approveLabAssumptions: event.target.checked }),
                );
                setExperiment({ status: "ready", evidence: null, message: "Calibration changed. Previous experiment results are stale.", requestId: null });
              }}
              disabled={calibration.status === "running"}
            />
            I explicitly accept laboratory assumptions for this synthetic fixture
          </label>
          <button className="primary" type="button" onClick={runCalibration} disabled={calibration.status === "running"}>
            {calibration.status === "running" ? "Constructing baseline…" : "Construct baseline"}
          </button>
          {calibration.status === "failed" ? <p className="alert" role="alert">{calibration.message}</p> : null}
          {calibration.evidence ? (
            <>
              <h3>Baseline status</h3>
              <dl>
                <dt>Status</dt>
                <dd>{baselineStatusLabel(calibration.evidence)}</dd>
                <dt>Readiness</dt>
                <dd>{calibration.evidence.readinessStatus}</dd>
                <dt>Hybrid compatible</dt>
                <dd>{calibration.evidence.hybridCompatible ? "yes" : "no"}</dd>
                <dt>Model fingerprint</dt>
                <dd>{calibration.evidence.modelFingerprint ?? "none"}</dd>
              </dl>
              <h3>Assumption review</h3>
              <p>Assumptions are not auto-approved. Unchecked construction refuses missing capacity/service parameters.</p>
              <table className="compare">
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Value</th>
                    <th>Unit</th>
                    <th>Origin</th>
                    <th>Identifiability</th>
                  </tr>
                </thead>
                <tbody>
                  {(calibration.evidence.parameterEstimates ?? []).map((item) => (
                    <tr key={item.parameterId}>
                      <td>{item.parameterId}</td>
                      <td>{item.value == null ? "unknown" : String(item.value)}</td>
                      <td>{item.unit ?? "—"}</td>
                      <td>{item.origin}</td>
                      <td>{item.identifiabilityStatus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <h3>Historical validation</h3>
              <p>
                {calibration.evidence.validationReport
                  ? `${calibration.evidence.validationReport.overallOutcome} (${calibration.evidence.validationReport.validationClass ?? calibration.evidence.validationReport.mode})`
                  : "No independent holdout report."}
              </p>
              {calibration.evidence.constructedModel ? (
                <button className="primary" type="button" onClick={() => setSection("lab")}>
                  Configure transformation experiment
                </button>
              ) : (
                <p>{calibration.evidence.blockedReason ?? "No model was constructed."}</p>
              )}
            </>
          ) : null}
        </section>
      ) : null}

      {section === "lab" && phase === "ready" ? (
        <section>
          {!calibration.evidence?.constructedModel ? (
            <p className="status" role="status">Construct a baseline first. The lab compares alternatives against one immutable constructed model.</p>
          ) : (
            <>
              <dl>
                <dt>Shared baseline</dt>
                <dd>{baselineStatusLabel(calibration.evidence)}</dd>
                <dt>Fingerprint</dt>
                <dd>{calibration.evidence.modelFingerprint}</dd>
              </dl>
              <h3>Alternatives</h3>
              <label className="inline">
                <input type="checkbox" checked={transform.includeCapacity} onChange={(event) => updateTransform({ includeCapacity: event.target.checked })} disabled={experiment.status === "running"} />
                Human capacity expansion
              </label>
              {transform.includeCapacity ? (
                <>
                  <label className="stack">
                    Additional triage staff
                    <select value={transform.extraTriageCapacity} onChange={(event) => updateTransform({ extraTriageCapacity: Number(event.target.value) })} disabled={experiment.status === "running"}>
                      {[0, 1, 2, 3].map((value) => (
                        <option key={value} value={value}>+{value}</option>
                      ))}
                    </select>
                  </label>
                  <label className="stack">
                    Additional resolution staff
                    <select value={transform.extraResolutionCapacity} onChange={(event) => updateTransform({ extraResolutionCapacity: Number(event.target.value) })} disabled={experiment.status === "running"}>
                      {[0, 1, 2, 3].map((value) => (
                        <option key={value} value={value}>+{value}</option>
                      ))}
                    </select>
                  </label>
                </>
              ) : null}
              <label className="inline">
                <input type="checkbox" checked={transform.includeAssisted} onChange={(event) => updateTransform({ includeAssisted: event.target.checked })} disabled={experiment.status === "running"} />
                AI-assisted processing (effective-mean model)
              </label>
              {transform.includeAssisted ? (
                <>
                  <label className="stack">
                    Stage
                    <select value={transform.stageId} onChange={(event) => updateTransform({ stageId: event.target.value })} disabled={experiment.status === "running"}>
                      <option value="triage">Triage</option>
                      <option value="resolution">Resolution</option>
                    </select>
                  </label>
                  <label className="stack">
                    Coverage
                    <select value={transform.coverage} onChange={(event) => updateTransform({ coverage: Number(event.target.value) })} disabled={experiment.status === "running"}>
                      {[0.25, 0.5, 0.75, 1].map((value) => (
                        <option key={value} value={value}>{Math.round(value * 100)}%</option>
                      ))}
                    </select>
                  </label>
                  <label className="stack">
                    Processing-time reduction
                    <select value={transform.processingReduction} onChange={(event) => updateTransform({ processingReduction: Number(event.target.value) })} disabled={experiment.status === "running"}>
                      {[0.2, 0.4, 0.6].map((value) => (
                        <option key={value} value={value}>{Math.round(value * 100)}%</option>
                      ))}
                    </select>
                  </label>
                </>
              ) : null}
              <label className="inline">
                <input
                  type="checkbox"
                  checked={transform.includeHybrid && hybridOk}
                  onChange={(event) => updateTransform({ includeHybrid: event.target.checked })}
                  disabled={experiment.status === "running" || !hybridOk}
                />
                Hybrid automation (existing completion route)
              </label>
              {hybridOk ? (
                transform.includeHybrid ? (
                  <label className="stack">
                    Auto-complete fraction of the existing triage completion option
                    <select value={transform.autoCompleteFraction} onChange={(event) => updateTransform({ autoCompleteFraction: Number(event.target.value) })} disabled={experiment.status === "running"}>
                      {[0.1, 0.25, 0.4].map((value) => (
                        <option key={value} value={value}>{Math.round(value * 100)}%</option>
                      ))}
                    </select>
                  </label>
                ) : null
              ) : (
                <p className="status">
                  This baseline does not support automated resolution. Select the hybrid-capable transformation baseline.
                  <button className="secondary" type="button" onClick={() => { setSection("baseline"); }}>
                    Open baseline selection
                  </button>
                </p>
              )}
              <h3>Execution</h3>
              <p>Shared demand, empty system, seed 20261127. {transform.runCount < 8 ? "Evidence is exploratory at this replication count." : ""} Session-only: refreshing Jira discards results.</p>
              <label className="stack">
                Items
                <select value={transform.itemCount} onChange={(event) => updateTransform({ itemCount: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[20, 40, 80].map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </label>
              <label className="stack">
                Replications
                <select value={transform.runCount} onChange={(event) => updateTransform({ runCount: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[2, 5, 8].map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </label>
              <button className="primary" type="button" onClick={runExperiment} disabled={experiment.status === "running"}>
                {experiment.status === "running" ? "Running comparison…" : "Run multi-scenario experiment"}
              </button>
              {experiment.status === "running" ? <p className="banner">Simulation is running. The interface is waiting for the remote, not frozen.</p> : null}
              {experiment.status === "failed" || experiment.status === "timeout" || experiment.status === "invalid" ? (
                <p className="alert" role="alert">{experiment.message}</p>
              ) : null}
              {experiment.status === "stale" ? <p className="status">{experiment.message}</p> : null}
              <h3>Assumption sensitivity</h3>
              <p>One parameter, three catalog values, same comparison engine. Distinct from Monte Carlo variability.</p>
              <label className="stack">
                Parameter
                <select value={transform.sensitivityParameter} onChange={(event) => updateTransform({ sensitivityParameter: event.target.value })} disabled={experiment.status === "running"}>
                  <option value="coverage">AI coverage</option>
                  <option value="processingReduction">AI processing-time reduction</option>
                  <option value="autoCompleteFraction">Automated completion fraction</option>
                  <option value="extraResolutionCapacity">Human resolution capacity</option>
                </select>
              </label>
              <button className="secondary" type="button" onClick={runSensitivity} disabled={experiment.status === "running" || sensitivity.status === "running"}>
                {sensitivity.status === "running" ? "Running sensitivity…" : "Run sensitivity experiment"}
              </button>
              {sensitivity.status === "failed" || sensitivity.status === "invalid" ? <p className="alert" role="alert">{sensitivity.message}</p> : null}
              {sensitivity.evidence ? <ResultsPanel evidence={sensitivity.evidence} transform={transform} /> : null}
            </>
          )}
          <details>
            <summary>Legacy connectivity comparison (CG-1)</summary>
            <p>Synthetic Support Operations Product Baseline. This path does not use the calibrated model.</p>
            <label className="stack">
              Intervention
              <select value={config.intervention} onChange={(event) => updateConfig({ intervention: event.target.value })} disabled={run.status === "running"}>
                {Object.values(INTERVENTIONS).map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </select>
            </label>
            <label className="stack">
              {config.intervention === "add-capacity" ? "Additional Level 1 capacity" : "Triage duration reduction"}
              <select
                value={parameterValue}
                onChange={(event) =>
                  updateConfig(
                    config.intervention === "add-capacity"
                      ? { extraCapacity: Number(event.target.value) }
                      : { triageReductionPercent: Number(event.target.value) },
                  )
                }
                disabled={run.status === "running"}
              >
                {intervention.options.map((option) => (
                  <option key={option} value={option}>
                    {config.intervention === "add-capacity" ? `+${option}` : `${option}%`}
                  </option>
                ))}
              </select>
            </label>
            <button className="secondary" type="button" onClick={runComparison} disabled={run.status === "running"}>
              {run.status === "running" ? "Running comparison…" : "Run connectivity comparison"}
            </button>
            {run.status === "completed" && run.evidence ? (
              <dl>
                <dt>Baseline cycle time</dt>
                <dd>{metric(run.evidence.baselineCycleTime?.mean)}</dd>
                <dt>Intervention cycle time</dt>
                <dd>{metric(run.evidence.scenarioCycleTime?.mean)}</dd>
                <dt>Integrity</dt>
                <dd>{run.evidence.integrityStatus}</dd>
              </dl>
            ) : null}
          </details>
        </section>
      ) : null}

      {section === "results" && phase === "ready" ? (
        <ResultsPanel evidence={experiment.evidence} transform={transform} />
      ) : null}

      {section === "decision" && phase === "ready" ? (
        <DecisionPanel
          experiment={experiment}
          economics={economics}
          assumptions={assumptions}
          constraints={constraints}
          exploreParameter={exploreParameter}
          onAssumptions={updateAssumptions}
          onConstraints={updateConstraints}
          onEvaluate={() => runEconomics()}
          onExplore={() => {
            const current = Number(assumptions[exploreParameter] ?? 0);
            const high = exploreParameter === "realizationRate" ? 1 : Math.max(current * 2, current + 1);
            runEconomics({
              strategyId: exploreStrategy,
              parameter: exploreParameter,
              low: 0,
              high,
              pointCount: 7,
            });
          }}
          onExploreParameter={setExploreParameter}
          exploreStrategy={exploreStrategy}
          onExploreStrategy={setExploreStrategy}
        />
      ) : null}

      <footer>
        <p>
          Minimized operational evidence may leave Forge for calibration and simulation. Arbitrary models are rejected.
          A faster task is not automatically a better operation.
        </p>
      </footer>
    </main>
  );
}
