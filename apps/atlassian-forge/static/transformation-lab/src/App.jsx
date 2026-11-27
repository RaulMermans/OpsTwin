import { useEffect, useRef, useState } from "react";
import { invoke, view } from "@forge/bridge";
import {
  INTERVENTIONS,
  WINDOW_PRESETS,
  afterConfigChange,
  afterFailedImport,
  comparisonPayload,
  defaultConfig,
  defaultImportConfig,
  metricById,
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
        Development integration — CG-2
      </p>
      <h1 style={{ margin: "8px 0 4px" }}>OpsTwin for Jira</h1>
      <h2 style={{ margin: "0 0 16px", fontWeight: 500 }}>AI Transformation Lab</h2>
      <p>Simulate before you automate. Observed Jira records are evidence, not a calibrated model. Synthetic simulation remains a separate lab.</p>

      <nav aria-label="Lab sections" style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        {["overview", "data", "simulation"].map((id) => (
          <button key={id} type="button" onClick={() => setSection(id)} aria-current={section === id}>
            {id === "overview" ? "Overview" : id === "data" ? "Operational Data" : "Simulation Lab"}
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
          Operational snapshots stay inside the Forge resolver. The simulation remote still accepts only the synthetic CG-1
          catalog. A faster task is not automatically a better operation.
        </p>
      </footer>
    </main>
  );
}
