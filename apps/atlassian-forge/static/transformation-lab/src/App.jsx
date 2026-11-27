import { useEffect, useRef, useState } from "react";
import { invoke, view } from "@forge/bridge";
import { INTERVENTIONS, afterConfigChange, comparisonPayload, defaultConfig } from "./labState.js";

function metric(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "unavailable";
  return Number(value).toFixed(3);
}

export function App() {
  const [phase, setPhase] = useState("initial");
  const [identity, setIdentity] = useState(null);
  const [project, setProject] = useState(null);
  const [requestTypes, setRequestTypes] = useState(null);
  const [config, setConfig] = useState(defaultConfig());
  const [run, setRun] = useState({ status: "ready", evidence: null, message: null, remoteStatus: "not checked" });
  const running = useRef(false);

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

  const intervention = INTERVENTIONS[config.intervention];
  const projectOk = project?.classification === "ok";
  const jiraStatus = projectOk ? "connected" : phase === "loading-project" ? "checking" : "blocked";
  const parameterValue =
    config.intervention === "add-capacity" ? config.extraCapacity : config.triageReductionPercent;

  return (
    <main style={{ fontFamily: "ui-sans-serif, system-ui, sans-serif", padding: "24px", maxWidth: "760px", color: "#172B4D" }}>
      <p style={{ letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "12px", color: "#44546F" }}>
        Development integration — CG-1
      </p>
      <h1 style={{ margin: "8px 0 4px" }}>OpsTwin for Jira</h1>
      <h2 style={{ margin: "0 0 16px", fontWeight: 500 }}>AI Transformation Lab</h2>
      <p>Simulate before you automate. Results come from the existing OpsTwin engine using a synthetic support model, not from this Jira project’s ticket history.</p>

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
          <dt>Remote connection</dt>
          <dd>{run.remoteStatus}</dd>
          <dt>Last verified operation</dt>
          <dd>{run.status === "completed" ? "synthetic comparison" : run.status}</dd>
        </dl>
      </section>

      {phase === "loading-project" ? <p>Loading project…</p> : null}
      {phase === "project-denied" ? (
        <p role="alert">{project?.message ?? "This user cannot access the current project."}</p>
      ) : null}
      {phase === "failed" ? <p role="alert">{run.message}</p> : null}

      {phase === "ready" ? (
        <section>
          <h3>Experiment configuration</h3>
          <p>Synthetic baseline: Support Operations Product Baseline (100 items, seed {config.runCount === 5 ? "20260716" : config.runCount}).</p>
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
        </section>
      ) : null}

      {run.status === "running" ? <p>Running…</p> : null}
      {run.status === "timeout" ? <p role="alert">The comparison timed out. {run.message}</p> : null}
      {run.status === "failed" && phase === "ready" ? <p role="alert">{run.message}</p> : null}
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
            {run.evidence.slaAttainmentBaseline === undefined || run.evidence.slaAttainmentBaseline === null ? null : (
              <>
                <dt>SLA attainment (baseline / scenario)</dt>
                <dd>
                  {metric(run.evidence.slaAttainmentBaseline)} / {metric(run.evidence.slaAttainmentScenario)}
                </dd>
              </>
            )}
          </dl>
          <p>{run.evidence.improvementInterpretation}</p>
        </section>
      ) : null}

      <footer>
        <h3>Evidence</h3>
        <p>
          Seed {run.evidence?.baseSeed ?? 20260716}. Engine contract 0.5.0. Synthetic catalog only. This integration does
          not ingest Jira issue descriptions or claim that a faster task is a better operation.
        </p>
      </footer>
    </main>
  );
}
