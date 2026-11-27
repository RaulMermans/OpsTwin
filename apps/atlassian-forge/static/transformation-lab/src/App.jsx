import { useEffect, useRef, useState } from "react";
import { invoke, view } from "@forge/bridge";
import {
  INTERVENTIONS,
  WINDOW_PRESETS,
  afterCalibrationChange,
  afterConfigChange,
  afterFailedImport,
  calibrationPayload,
  comparisonPayload,
  defaultConfig,
  defaultImportConfig,
  defaultTransform,
  metricById,
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
    fixtureId: "cg3-golden-analytical",
    approveLabAssumptions: false,
  });
  const [transform, setTransform] = useState(defaultTransform());
  const [experiment, setExperiment] = useState({ status: "ready", evidence: null, message: null });
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

  async function runCalibration() {
    if (calibrating.current || phase !== "ready") return;
    calibrating.current = true;
    setCalibration((current) => ({ ...current, status: "running", evidence: null, message: null }));
    try {
      const result = await invoke(
        "runSyntheticCalibration",
        calibrationPayload(calibration.fixtureId, calibration.approveLabAssumptions),
      );
      if (result?.status === "ok" && result.evidence) {
        setCalibration((current) => ({
          ...current,
          status: "completed",
          evidence: result.evidence,
          message: result.evidence.disclosure,
        }));
      } else {
        setCalibration((current) => ({
          ...current,
          status: "failed",
          evidence: null,
          message: result?.message ?? "Synthetic calibration failed.",
        }));
      }
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

  function updateTransform(patch) {
    setTransform((current) => ({ ...current, ...patch }));
    setExperiment((previous) =>
      previous.evidence
        ? { status: "ready", evidence: null, message: "Previous results are stale because the configuration changed." }
        : previous,
    );
  }

  async function runExperiment() {
    if (experimenting.current || phase !== "ready") return;
    if (!calibration.evidence?.constructedModel) {
      setExperiment({
        status: "failed",
        evidence: null,
        message: "Calibrate a constructed baseline first. Interventions are not run against structurally invalid models.",
      });
      return;
    }
    experimenting.current = true;
    setExperiment({ status: "running", evidence: null, message: null });
    try {
      const result = await invoke("runTransformationExperiment", transformPayload(calibration, transform));
      if (result?.status === "ok" && result.evidence) {
        setExperiment({ status: "completed", evidence: result.evidence, message: result.evidence.disclosure });
      } else {
        setExperiment({
          status: "failed",
          evidence: null,
          message: result?.message ?? "The transformation experiment failed.",
        });
      }
    } catch (caught) {
      setExperiment({
        status: "failed",
        evidence: null,
        message: caught instanceof Error ? caught.message : "The transformation experiment failed.",
      });
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

  return (
    <main style={{ fontFamily: "ui-sans-serif, system-ui, sans-serif", padding: "24px", maxWidth: "760px", color: "#172B4D" }}>
      <p style={{ letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "12px", color: "#44546F" }}>
        Development integration — CG-4
      </p>
      <h1 style={{ margin: "8px 0 4px" }}>OpsTwin for Jira</h1>
      <h2 style={{ margin: "0 0 16px", fontWeight: 500 }}>AI Transformation Lab</h2>
      <p>Simulate before you automate. Observed Jira records are evidence, not a calibrated model. Synthetic simulation remains a separate lab.</p>

      <nav aria-label="Lab sections" style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        {["overview", "data", "calibration", "experiments", "simulation"].map((id) => (
          <button key={id} type="button" onClick={() => setSection(id)} aria-current={section === id}>
            {id === "overview"
              ? "Overview"
              : id === "data"
                ? "Operational Data"
                : id === "calibration"
                  ? "Model Calibration"
                  : id === "experiments"
                    ? "Experiments"
                    : "Connectivity Lab"}
          </button>
        ))}
      </nav>

      {phase === "loading-project" ? <p>Loading project…</p> : null}
      {phase === "project-denied" ? (
        <p role="alert">{project?.message ?? "This user cannot access the current project."}</p>
      ) : null}
      {phase === "failed" ? <p role="alert">{run.message}</p> : null}

      {section === "overview" ? (
        <section>
          <h3>Connection status</h3>
          <dl>
            <dt>Project</dt>
            <dd>{projectOk ? `${project.name} (${project.projectKey})` : identity?.projectKey ?? "not provided by Forge context"}</dd>
            <dt>Jira connection</dt>
            <dd>{jiraStatus}</dd>
            <dt>Request types</dt>
            <dd>
              {requestTypes?.classification === "empty"
                ? "none visible"
                : requestTypes?.requestTypes?.length
                  ? requestTypes.requestTypes.map((item) => item.name).join(", ")
                  : requestTypes?.message ?? "not loaded"}
            </dd>
            <dt>Operational snapshot</dt>
            <dd>{importState.status === "none" ? "no data imported" : `${importState.status}${importState.mode === "synthetic-demo" ? " (synthetic demonstration)" : ""}`}</dd>
            <dt>Remote connection</dt>
            <dd>{run.remoteStatus}</dd>
          </dl>
        </section>
      ) : null}

      {section === "data" && phase === "ready" ? (
        <section>
          <h3>Source</h3>
          <p>
            Connected project {project?.name} ({project?.projectKey}). Service desk{" "}
            {requestTypes?.serviceDeskId ?? "not visible"}. Authorization follows the signed-in Jira user.
          </p>
          <h3>Import configuration</h3>
          <p>
            This reads Jira/JSM issues for the connected project. Simulation Lab results are not operational records and
            cannot be imported here.
          </p>
          <p>Read-only import of issue metadata, changelogs, worklogs, and SLA cycles. Descriptions, comments, and attachments are not retrieved.</p>
          <label>
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
          <p>Record limit 40 cases. Cohort includes cases open during the window, not only those created in it.</p>
          <button type="button" onClick={runImport} disabled={importState.status === "running"}>
            {importState.status === "running" ? "Importing…" : "Import operational records"}
          </button>
          <button type="button" onClick={runSyntheticDemo} disabled={importState.status === "running"}>
            Load synthetic demonstration
          </button>
          {importState.status === "running" ? <p>Import in progress{importState.stage ? `: ${importState.stage}` : ""}.</p> : null}
          {importState.status === "failed" || importState.status === "rate_limited" || importState.status === "timeout" ? (
            <p role="alert">
              {importState.status}: {importState.message}
              {importState.stale ? " The previous snapshot is not shown as current." : ""}
            </p>
          ) : null}
          {importState.status === "none" ? <p>No data imported.</p> : null}
          {snapshot ? (
            <>
              {importState.mode === "synthetic-demo" ? (
                <p role="status">Synthetic demonstration. These records are not this project&apos;s live history.</p>
              ) : null}
              {snapshot.completenessStatus === "empty" ? <p>Valid empty dataset: the query succeeded and observed no cases.</p> : null}
              {importState.status === "partial" ? <p role="status">Partial import. Extraction was truncated.</p> : null}
              {snapshot.readiness === "invalid" ? <p role="alert">Invalid snapshot.</p> : null}
              {snapshot.readiness === "insufficient_for_calibration" ? <p>Insufficient evidence for future calibration assessment.</p> : null}
              <h3>Snapshot overview</h3>
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
                <dd>
                  {JSON.stringify(metricById(snapshot, "request_type_distribution")?.value ?? [])}
                </dd>
                <dt>Cycle time (p50 minutes)</dt>
                <dd>{cycle?.value?.p50 ?? "unavailable"}</dd>
                <dt>Open at window end</dt>
                <dd>{metricById(snapshot, "open_cases_at_window_end")?.value ?? "unavailable"}</dd>
                <dt>Resolved</dt>
                <dd>{metricById(snapshot, "resolution_count")?.value ?? "unavailable"}</dd>
              </dl>
              <h3>Data quality</h3>
              <ul>
                {snapshot.dataQuality.map((item) => (
                  <li key={item.metricId}>{qualityLine(item)}</li>
                ))}
              </ul>
              <h3>Provenance</h3>
              <dl>
                <dt>Source</dt>
                <dd>
                  {snapshot.sourceSystem} / {snapshot.sourceProject.key} ({snapshot.provenance.evidenceClass},{" "}
                  {snapshot.provenance.transportAuthenticity})
                </dd>
                <dt>Import time</dt>
                <dd>{snapshot.importTimestamp}</dd>
                <dt>Snapshot ID</dt>
                <dd>{snapshot.snapshotId}</dd>
                <dt>Content fingerprint</dt>
                <dd>{snapshot.contentFingerprint}</dd>
                <dt>Completeness</dt>
                <dd>
                  {snapshot.completenessStatus} / {snapshot.readiness}
                </dd>
              </dl>
              <p>{snapshot.limitations.join(" ")}</p>
            </>
          ) : null}
        </section>
      ) : null}

      {section === "calibration" && phase === "ready" ? (
        <section>
          <h3>Synthetic model calibration</h3>
          <p role="status">
            This path loads a controlled laboratory fixture on the remote. It does not send imported Jira snapshots and is not
            organizational calibration.
          </p>
          <label>
            Laboratory fixture
            <select
              value={calibration.fixtureId}
              onChange={(event) => {
                setCalibration((current) => afterCalibrationChange({ ...current, fixtureId: event.target.value }));
                setExperiment({ status: "ready", evidence: null, message: "Calibration changed. Previous experiment results are stale." });
              }}
              disabled={calibration.status === "running"}
            >
              <option value="cg3-golden-analytical">Golden analytical (synthetic)</option>
              <option value="cg3-partially-observable">Partially observable (assumptions required)</option>
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={calibration.approveLabAssumptions}
              onChange={(event) => {
                setCalibration((current) =>
                  afterCalibrationChange({ ...current, approveLabAssumptions: event.target.checked }),
                );
                setExperiment({ status: "ready", evidence: null, message: "Calibration changed. Previous experiment results are stale." });
              }}
              disabled={calibration.status === "running"}
            />
            Accept laboratory assumptions for this synthetic fixture
          </label>
          <button type="button" onClick={runCalibration} disabled={calibration.status === "running"}>
            {calibration.status === "running" ? "Calibrating…" : "Run synthetic calibration"}
          </button>
          {calibration.status === "failed" ? <p role="alert">{calibration.message}</p> : null}
          {calibration.evidence ? (
            <>
              <h3>Evidence readiness</h3>
              <dl>
                <dt>Disclosure</dt>
                <dd>{calibration.evidence.disclosure}</dd>
                <dt>Readiness</dt>
                <dd>{calibration.evidence.readinessStatus}</dd>
                <dt>Historically adequate</dt>
                <dd>{calibration.evidence.readinessStatus === "validated_for_defined_scope" ? "yes, for the recorded scope" : "no"}</dd>
                <dt>Failure class</dt>
                <dd>{calibration.evidence.failureClass ?? "none"}</dd>
                <dt>Snapshot fingerprint</dt>
                <dd>{calibration.evidence.sourceSnapshotFingerprint}</dd>
              </dl>
              <h3>Estimated parameters</h3>
              <ul>
                {(calibration.evidence.parameterEstimates ?? [])
                  .filter((item) => item.origin === "empirical_estimate" && item.consumedByModel !== false)
                  .map((item) => (
                    <li key={item.parameterId}>
                      {item.parameterId}: {String(item.value)} ({item.identifiabilityStatus})
                    </li>
                  ))}
              </ul>
              <h3>Assumptions</h3>
              <ul>
                {(calibration.evidence.parameterEstimates ?? [])
                  .filter((item) => item.origin === "approved_assumption" || item.origin === "structural_constraint")
                  .map((item) => (
                    <li key={item.parameterId}>
                      {item.parameterId}: {String(item.value)} ({item.origin})
                    </li>
                  ))}
              </ul>
              <h3>Unknown or diagnostic parameters</h3>
              <ul>
                {(calibration.evidence.parameterEstimates ?? [])
                  .filter((item) => item.value == null || item.consumedByModel === false)
                  .map((item) => (
                    <li key={item.parameterId}>
                      {item.parameterId}: unknown ({item.identifiabilityStatus})
                    </li>
                  ))}
              </ul>
              <h3>Constructed model</h3>
              <p>
                {calibration.evidence.constructedModel
                  ? `Fingerprint ${calibration.evidence.modelFingerprint}. A constructed model is not a historically adequate model.`
                  : calibration.evidence.blockedReason ?? "No model was constructed."}
              </p>
              <h3>Historical validation</h3>
              <p>
                {calibration.evidence.validationReport
                  ? `${calibration.evidence.validationReport.overallOutcome} (${calibration.evidence.validationReport.validationClass ?? calibration.evidence.validationReport.mode})`
                  : "No independent holdout report. Failed and inconclusive outcomes stay failed or inconclusive."}
              </p>
            </>
          ) : null}
        </section>
      ) : null}

      {section === "experiments" && phase === "ready" ? (
        <section>
          <h3>Human-only baseline</h3>
          <p>
            The comparison baseline is the calibrated operation with no new AI intervention. Canonical models keep
            itemCount=1 as a structural placeholder. Experiments use a separate execution volume.
          </p>
          {!calibration.evidence?.constructedModel ? (
            <p role="status">Run synthetic calibration first. A constructed model is required before interventions.</p>
          ) : (
            <dl>
              <dt>Baseline class</dt>
              <dd>{calibration.evidence.readinessStatus}</dd>
              <dt>Historically adequate</dt>
              <dd>{calibration.evidence.readinessStatus === "validated_for_defined_scope" ? "for recorded holdout scope only" : "no — exploratory if executed"}</dd>
              <dt>Model fingerprint</dt>
              <dd>{calibration.evidence.modelFingerprint}</dd>
              <dt>Triage / resolution means</dt>
              <dd>
                {(calibration.evidence.parameterEstimates ?? [])
                  .filter((item) => item.parameterId?.includes("processing_time.mean") && item.consumedByModel !== false)
                  .map((item) => `${item.parameterId}=${item.value}`)
                  .join("; ") || "see calibration"}
              </dd>
              <dt>Capacities</dt>
              <dd>
                {(calibration.evidence.parameterEstimates ?? [])
                  .filter((item) => item.parameterId?.startsWith("resource.") && item.consumedByModel !== false)
                  .map((item) => `${item.parameterId}=${item.value}`)
                  .join("; ")}
              </dd>
            </dl>
          )}
          <h3>Intervention</h3>
          <label>
            Kind
            <select value={transform.kind} onChange={(event) => updateTransform({ kind: event.target.value })} disabled={experiment.status === "running"}>
              <option value="capacity">Human capacity expansion</option>
              <option value="ai_assisted">AI-assisted processing (effective mean)</option>
              <option value="hybrid">Hybrid automation (existing route shift)</option>
            </select>
          </label>
          {transform.kind === "capacity" ? (
            <>
              <label>
                Additional triage staff
                <select value={transform.extraTriageCapacity} onChange={(event) => updateTransform({ extraTriageCapacity: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[0, 1, 2, 3].map((value) => (
                    <option key={value} value={value}>
                      +{value}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Additional resolution staff
                <select value={transform.extraResolutionCapacity} onChange={(event) => updateTransform({ extraResolutionCapacity: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[0, 1, 2, 3].map((value) => (
                    <option key={value} value={value}>
                      +{value}
                    </option>
                  ))}
                </select>
              </label>
            </>
          ) : null}
          {transform.kind === "ai_assisted" ? (
            <>
              <p>Effective-mean model, not per-case AI execution or mixture tails.</p>
              <label>
                Stage
                <select value={transform.stageId} onChange={(event) => updateTransform({ stageId: event.target.value })} disabled={experiment.status === "running"}>
                  <option value="triage">Triage</option>
                  <option value="resolution">Resolution</option>
                </select>
              </label>
              <label>
                Coverage
                <select value={transform.coverage} onChange={(event) => updateTransform({ coverage: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[0.25, 0.5, 0.75, 1].map((value) => (
                    <option key={value} value={value}>
                      {Math.round(value * 100)}%
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Processing-time reduction on covered work
                <select value={transform.processingReduction} onChange={(event) => updateTransform({ processingReduction: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[0.2, 0.4, 0.6].map((value) => (
                    <option key={value} value={value}>
                      {Math.round(value * 100)}%
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Review overhead (minutes)
                <select value={transform.reviewOverheadMinutes} onChange={(event) => updateTransform({ reviewOverheadMinutes: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[0, 0.25, 0.5].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
            </>
          ) : null}
          {transform.kind === "hybrid" ? (
            <>
              <p>
                Auto-complete shifts the existing triage success route toward completion. It does not add an automation
                stage. Refused when that completion option is not already in the model.
              </p>
              <label>
                Auto-complete fraction
                <select value={transform.autoCompleteFraction} onChange={(event) => updateTransform({ autoCompleteFraction: Number(event.target.value) })} disabled={experiment.status === "running"}>
                  {[0.1, 0.25, 0.4].map((value) => (
                    <option key={value} value={value}>
                      {Math.round(value * 100)}%
                    </option>
                  ))}
                </select>
              </label>
            </>
          ) : null}
          <h3>Experiment execution</h3>
          <p>
            Demand volume {transform.itemCount} items, {transform.runCount} paired replications, seed 20261127. Empty
            system, no warm-up. This is not the calibration placeholder itemCount.
          </p>
          <label>
            Items
            <select value={transform.itemCount} onChange={(event) => updateTransform({ itemCount: Number(event.target.value) })} disabled={experiment.status === "running"}>
              {[20, 40, 80].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            Replications
            <select value={transform.runCount} onChange={(event) => updateTransform({ runCount: Number(event.target.value) })} disabled={experiment.status === "running"}>
              {[2, 5, 8].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={runExperiment} disabled={experiment.status === "running"}>
            {experiment.status === "running" ? "Running experiment…" : "Run comparative experiment"}
          </button>
          {experiment.status === "failed" ? <p role="alert">{experiment.message}</p> : null}
          {experiment.status === "ready" && experiment.message ? <p>{experiment.message}</p> : null}
          {experiment.evidence ? (
            <section>
              <h3>Comparative evidence</h3>
              <dl>
                <dt>Baseline class</dt>
                <dd>
                  {experiment.evidence.baselineClass}
                  {experiment.evidence.exploratory ? " (exploratory)" : ""}
                </dd>
                <dt>Approximations</dt>
                <dd>{(experiment.evidence.approximations ?? []).join(", ") || "none (capacity replacement)"}</dd>
                <dt>Identities agree</dt>
                <dd>{experiment.evidence.identitiesAgree ? "yes" : "no"}</dd>
                <dt>Executed item count</dt>
                <dd>{experiment.evidence.experiment?.itemCount}</dd>
                <dt>Baseline cycle time (mean, minutes)</dt>
                <dd>{metric(experiment.evidence.baselineCycleTime?.mean)}</dd>
                <dt>Intervention cycle time (mean, minutes)</dt>
                <dd>{metric(experiment.evidence.scenarioCycleTime?.mean)}</dd>
                <dt>Paired difference (mean)</dt>
                <dd>{metric(experiment.evidence.pairedDifference?.mean)}</dd>
                <dt>Improvement probability</dt>
                <dd>{metric(experiment.evidence.probabilityOfImprovement)}</dd>
                <dt>Integrity</dt>
                <dd>{experiment.evidence.integrityStatus}</dd>
              </dl>
              <p>{experiment.evidence.improvementInterpretation}</p>
              <h3>Disclosures</h3>
              <ul>
                {(experiment.evidence.disclosures ?? []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </section>
      ) : null}

      {section === "simulation" && phase === "ready" ? (
        <section>
          <h3>Experiment configuration</h3>
          <p>Synthetic baseline: Support Operations Product Baseline (100 items, seed {config.runCount === 5 ? "20260716" : config.runCount}). This path does not send imported Jira records to the simulation engine.</p>
          <label>
            Intervention
            <select
              value={config.intervention}
              onChange={(event) => updateConfig({ intervention: event.target.value })}
              disabled={run.status === "running"}
            >
              {Object.values(INTERVENTIONS).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
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
          <p>Paired runs: {config.runCount}. This is a connectivity-sized workload, not a statistically robust operational study.</p>
          <button type="button" onClick={runComparison} disabled={run.status === "running"}>
            {run.status === "running" ? "Running comparison…" : "Run comparison"}
          </button>
          {run.status === "running" ? <p>Running…</p> : null}
          {run.status === "timeout" ? <p role="alert">The comparison timed out. {run.message}</p> : null}
          {run.status === "failed" ? <p role="alert">{run.message}</p> : null}
          {run.status === "ready" && run.message ? <p>{run.message}</p> : null}
          {run.status === "completed" && run.evidence ? (
            <section>
              <h3>Results</h3>
              <dl>
                <dt>Baseline cycle time (mean, minutes)</dt>
                <dd>{metric(run.evidence.baselineCycleTime?.mean)}</dd>
                <dt>Intervention cycle time (mean, minutes)</dt>
                <dd>{metric(run.evidence.scenarioCycleTime?.mean)}</dd>
                <dt>Paired difference (mean)</dt>
                <dd>{metric(run.evidence.pairedDifference?.mean)}</dd>
                <dt>Improvement probability</dt>
                <dd>{metric(run.evidence.probabilityOfImprovement)}</dd>
                <dt>95% CI for the paired difference</dt>
                <dd>
                  {metric(run.evidence.pairedDifference?.lower)} to {metric(run.evidence.pairedDifference?.upper)}
                  {run.evidence.pairedDifference?.reliableSampleSize ? "" : " (sample size below the reliability threshold)"}
                </dd>
                <dt>Valid paired runs</dt>
                <dd>{run.evidence.validPairedRunCount}</dd>
                <dt>Integrity</dt>
                <dd>{run.evidence.integrityStatus}</dd>
              </dl>
              <p>{run.evidence.improvementInterpretation}</p>
            </section>
          ) : null}
        </section>
      ) : null}

      <footer>
        <h3>Evidence</h3>
        <p>
          Operational snapshots stay inside the Forge resolver. Calibration and experiments use synthetic fixture identifiers,
          not live Jira records. Experiments execute the existing comparison engine. A faster task is not automatically a
          better operation.
        </p>
      </footer>
    </main>
  );
}
