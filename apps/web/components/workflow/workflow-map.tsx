"use client";

import { useMemo, useRef, useState, type CSSProperties, type KeyboardEvent } from "react";

import type { ComparisonResult } from "../../lib/api/simulation";
import { asRecord, asRecords } from "../../lib/scenario-lab/result-adapter";
import { buildScenario, type ScenarioDraft } from "../../lib/scenarios/builders";
import type { BaselineForm } from "../../lib/templates/support";
import { normalizeOverlayValues, overlayOptions, workflowOverlayValues, type WorkflowOverlayMetric } from "../../lib/workflow/overlays";
import { buildWorkflowPresentation, type WorkflowNode, type WorkflowOperationalModel, type WorkflowPresentation } from "../../lib/workflow/presentation-model";
import { mapScenarioChanges, type WorkflowChange } from "../../lib/workflow/scenario-changes";

type Mode = "structure" | "changes" | "pressure" | "comparison";
const modes: { id: Mode; label: string }[] = [
  { id: "structure", label: "Structure" }, { id: "changes", label: "Scenario changes" },
  { id: "pressure", label: "Operational pressure" }, { id: "comparison", label: "Baseline vs scenario" },
];

type Props = { model: WorkflowOperationalModel | null; baseline: BaselineForm; scenarios: ScenarioDraft[]; result: ComparisonResult | null; guided?: boolean };

export function WorkflowVisualization({ model, baseline, scenarios, result, guided = false }: Props) {
  const presentation = useMemo(() => buildWorkflowPresentation(model), [model]);
  const [mode, setMode] = useState<Mode>("structure");
  const [scenarioId, setScenarioId] = useState(scenarios[0]?.id ?? "");
  const [metric, setMetric] = useState<WorkflowOverlayMetric>("averageWaitingTime");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [listMode, setListMode] = useState(false);
  const nodeRefs = useRef(new Map<string, HTMLButtonElement>());
  const selectedScenario = scenarios.find((item) => item.id === scenarioId) ?? scenarios[0] ?? null;
  const scenario = selectedScenario ? buildScenario(selectedScenario, baseline) : null;
  const mappedChanges = useMemo(() => model ? mapScenarioChanges(model, scenario) : { changes: [], warnings: [] }, [model, scenario]);
  const resultScenario = result && selectedScenario ? asRecords(result.scenarios).find((item) => item.scenarioId === selectedScenario.id) ?? null : null;
  const hasEvidence = resultScenario?.status === "valid";
  const rawOverlay = useMemo(() => workflowOverlayValues(result, selectedScenario?.id ?? null, metric), [result, selectedScenario?.id, metric]);
  const intensity = useMemo(() => normalizeOverlayValues(rawOverlay), [rawOverlay]);
  const selected = presentation.nodes.find((node) => node.id === selectedId) ?? null;

  const closeInspector = () => {
    const ref = selectedId ? nodeRefs.current.get(selectedId) : null;
    ref?.focus();
    setSelectedId(null);
  };
  const handleKey = (event: KeyboardEvent<HTMLElement>) => { if (event.key === "Escape" && selectedId) { event.preventDefault(); closeInspector(); } };

  return <section className="workflow-section" aria-labelledby="workflow-title" onKeyDown={handleKey}>
    <div className="workflow-heading"><div><p className="eyebrow">{guided ? "Process being simulated" : "Operational model"}</p><h2 id="workflow-title">{guided ? "Process" : "Flow"}</h2><p>{guided ? "See the current process, proposed changes, and where queues build up." : "Trace structure, explicit changes, and returned evidence without changing the simulation model."}</p></div><button type="button" className="secondary" onClick={() => setListMode((value) => !value)}>{listMode ? "View as map" : "View as list"}</button></div>
    <div className="workflow-controls" aria-label={guided ? "Process display controls" : "Flow display controls"}>
      <div className="workflow-modes" aria-label={guided ? "Process views" : "Flow modes"}>{modes.map((item) => <button type="button" key={item.id} aria-pressed={mode === item.id} disabled={(item.id === "pressure" || item.id === "comparison") && !hasEvidence} onClick={() => setMode(item.id)}>{guided ? ({ structure: "Current process", changes: "Proposed changes", pressure: "Where queues build up", comparison: "Current operation vs change" }[item.id]) : item.label}</button>)}</div>
      {scenarios.length > 0 && <label>{guided ? "Change to inspect" : "Scenario"}<select aria-label={guided ? "Change to inspect" : "Flow scenario"} value={selectedScenario?.id ?? ""} onChange={(event) => setScenarioId(event.target.value)}>{scenarios.map((item) => <option key={item.id} value={item.id}>{item.name || item.id}</option>)}</select></label>}
      {mode === "pressure" && <label>Evidence<select aria-label="Pressure evidence" value={metric} onChange={(event) => setMetric(event.target.value as WorkflowOverlayMetric)}>{overlayOptions.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>}
    </div>
    {!presentation.valid && <div className="workflow-warning" role="status"><strong>Some workflow relationships are unavailable.</strong><ul>{presentation.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
    {mappedChanges.warnings.length > 0 && <div className="workflow-warning" role="status"><strong>Some scenario targets are unavailable.</strong><ul>{mappedChanges.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
    {mode === "changes" && scenarios.length === 0 && <p className="empty-state">Add a scenario to inspect explicit changes.</p>}
    {(mode === "pressure" || mode === "comparison") && !hasEvidence && <p className="empty-state">Run a valid comparison to inspect returned entity evidence.</p>}
    {mode === "pressure" && hasEvidence && <p className="workflow-scale-note">Relative intensity within the current result</p>}
    <div className={`workflow-content ${listMode ? "show-list" : "show-map"} ${mode === "changes" && mappedChanges.changes.length > 0 ? "has-changes" : ""} ${selected ? "has-inspector" : ""}`}>
      {mode === "changes" && mappedChanges.changes.length > 0 && <div className="workflow-change-summary" aria-label="Selected scenario changes"><strong>{guided ? "What this change modifies" : "Explicit changes"} in {selectedScenario?.name}</strong><ul>{mappedChanges.changes.map((change) => <li key={change.id}>{change.entityId} — {changeLabel(change)} ({change.direction})</li>)}</ul></div>}
      {!listMode && <div className="workflow-canvas" aria-label="Support workflow map">
        <svg className="workflow-connectors" viewBox="0 0 1000 600" aria-hidden="true" focusable="false">{presentation.edges.map((edge) => { const changed = mode === "changes" && mappedChanges.changes.some((item) => item.targetIds.includes(edge.id)); return <g key={edge.id} className={changed ? "changed" : ""}><path d={edge.path} className={edge.rework ? "rework" : "standard"} /><text><textPath href={`#${edge.id}`}>{changed ? `${edge.label} · changed` : edge.label}</textPath></text><path id={edge.id} d={edge.path} className="label-path" /></g>; })}</svg>
        <div className="workflow-grid">{presentation.nodes.map((node) => {
          const change = mappedChanges.changes.find((item) => item.targetIds.includes(node.id));
          const value = rawOverlay[node.id] ?? null; const scaled = intensity[node.id] ?? null;
          const showChange = mode === "changes" && Boolean(change); const showPressure = mode === "pressure" && overlayMatchesNode(metric, node);
          const style = { "--workflow-row": node.row + 1, "--workflow-column": node.column + 1, "--pressure": scaled ?? 0 } as CSSProperties;
          const overlayLabel = showPressure ? `${overlayOptions.find((item) => item.id === metric)?.label}: ${formatEvidence(metric, value)}` : null;
          const label = `${node.label}, ${node.kind}${showChange ? ", changed" : ""}${overlayLabel ? `, ${overlayLabel}` : ""}`;
          return <button key={node.id} ref={(element) => { if (element) nodeRefs.current.set(node.id, element); else nodeRefs.current.delete(node.id); }} type="button" className={`workflow-node ${node.kind} ${selectedId === node.id ? "selected" : ""} ${showChange ? "changed" : ""} ${showPressure ? "pressure" : ""} ${showPressure && value === null ? "unavailable" : ""}`} style={style} aria-label={label} aria-pressed={selectedId === node.id} onClick={() => setSelectedId(node.id)}>
            <span className="workflow-node-kind">{node.kind}</span><strong>{node.label}</strong><small>{nodeAssumption(node, model)}</small>{showChange && change && <span className="workflow-change-badge">{changeLabel(change)}</span>}{showPressure && <span className="workflow-value">{overlayLabel}</span>}
          </button>;
        })}</div>
      </div>}
      <WorkflowTextSummary presentation={presentation} changes={mode === "changes" ? mappedChanges.changes : []} overlay={mode === "pressure" ? rawOverlay : {}} metric={metric} visible={listMode} />
      {selected && <WorkflowInspector node={selected} model={model} presentation={presentation} change={mappedChanges.changes.find((item) => item.targetIds.includes(selected.id)) ?? null} mode={mode} result={result} scenario={resultScenario} onClose={closeInspector} />}
    </div>
  </section>;
}

function overlayMatchesNode(metric: WorkflowOverlayMetric, node: WorkflowNode) {
  const option = overlayOptions.find((item) => item.id === metric);
  return option?.kind === node.kind;
}

function nodeAssumption(node: WorkflowNode, model: WorkflowOperationalModel | null) {
  if (!model) return "Evidence unavailable";
  if (node.kind === "source") { const source = model.sources.find((item) => item.id === node.id); return source ? `${String(source.arrival?.type ?? "Arrival")} arrival` : "Source"; }
  if (node.kind === "stage") { const stage = model.stages.find((item) => item.id === node.id); const type = stage?.processingTime?.type; return type ? `${String(type)} processing` : "Processing stage"; }
  if (node.kind === "resource") { const resource = model.resourcePools.find((item) => item.id === node.id); return `Capacity ${resource?.capacity ?? "unavailable"}`; }
  return "Terminal outcome";
}

function fieldLabel(field: string) {
  if (field === "capacity") return "Capacity";
  if (field.includes("meanInterarrivalTime")) return "Mean arrival interval";
  if (field.includes("processing")) return "Processing time";
  if (field === "failure.probability") return "Failure probability";
  if (field === "targetDuration") return "SLA target";
  return field;
}
const displayValue = (value: unknown) => typeof value === "number" ? Number(value.toFixed(3)).toString() : value == null ? "Unavailable" : String(value);
const changeLabel = (change: WorkflowChange) => `${fieldLabel(change.field)}: ${displayValue(change.baselineValue)} → ${displayValue(change.scenarioValue)}`;

function formatEvidence(metric: string, value: number | null) {
  if (value === null) return "Unavailable";
  if (metric === "utilization" || metric === "idleCapacityProportion" || metric === "failureRate" || metric === "completionRate") return `${(value * 100).toFixed(1)}%`;
  return value.toFixed(2);
}

function WorkflowTextSummary({ presentation, changes, overlay, metric, visible }: { presentation: WorkflowPresentation; changes: WorkflowChange[]; overlay: Record<string, number | null>; metric: WorkflowOverlayMetric; visible: boolean }) {
  const content = <><ol aria-label="Workflow entities">{presentation.nodes.filter((node) => node.kind !== "resource").map((node) => <li key={node.id}><strong>{node.label}</strong> — {node.description}{changes.find((item) => item.targetIds.includes(node.id)) ? ` Change: ${changeLabel(changes.find((item) => item.targetIds.includes(node.id))!)}` : ""}{Object.hasOwn(overlay, node.id) ? ` ${overlayOptions.find((item) => item.id === metric)?.label}: ${formatEvidence(metric, overlay[node.id])}` : ""}</li>)}</ol><ul aria-label="Workflow relationships">{presentation.edges.map((edge) => <li key={edge.id}>{edge.description}</li>)}{presentation.resourceLinks.map((link) => <li key={link.id}>{presentation.nodes.find((node) => node.id === link.resourceId)?.label} supports {presentation.nodes.find((node) => node.id === link.stageId)?.label}.</li>)}</ul>{changes.length > 0 && <table><caption>Selected scenario changes</caption><thead><tr><th>Entity</th><th>Field</th><th>Baseline</th><th>Scenario</th><th>Direction</th></tr></thead><tbody>{changes.map((change) => <tr key={change.id}><th>{change.entityId}</th><td>{fieldLabel(change.field)}</td><td>{displayValue(change.baselineValue)}</td><td>{displayValue(change.scenarioValue)}</td><td>{change.direction}</td></tr>)}</tbody></table>}</>;
  if (visible) return <div className="workflow-list" role="region" aria-label="Workflow list view">{content}</div>;
  return <div className="sr-only">{content}</div>;
}

function aggregate(container: unknown, groupName: "stageMetrics" | "resourcePoolMetrics", idKey: "stageId" | "resourcePoolId", id: string, metric: string) {
  const group = asRecords(asRecord(container)?.[groupName]); const entry = group.find((item) => item[idKey] === id);
  const value = asRecord(asRecord(entry?.metrics)?.[metric])?.mean;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function systemMean(container: unknown, metric: string) {
  const value = asRecord(asRecord(container)?.systemMetrics)?.[metric]; const mean = asRecord(value)?.mean;
  return typeof mean === "number" && Number.isFinite(mean) ? mean : null;
}

function WorkflowInspector({ node, model, presentation, change, mode, result, scenario, onClose }: { node: WorkflowNode; model: WorkflowOperationalModel | null; presentation: WorkflowPresentation; change: WorkflowChange | null; mode: Mode; result: ComparisonResult | null; scenario: Record<string, unknown> | null; onClose: () => void }) {
  const stage = model?.stages.find((item) => item.id === node.entityId); const resource = model?.resourcePools.find((item) => item.id === node.entityId); const source = model?.sources.find((item) => item.id === node.entityId);
  const groupName = node.kind === "stage" ? "stageMetrics" : "resourcePoolMetrics"; const idKey = node.kind === "stage" ? "stageId" : "resourcePoolId";
  const comparisonMetrics = node.kind === "stage" ? ["averageWaitingTime", "timeWeightedQueueLength", "failureRate", "reworkCount", "visitCount"] : node.kind === "resource" ? ["utilization", "idleCapacityProportion", "meanRequestWait", "maximumConcurrentUsage"] : [];
  const variant = scenario?.status === "valid" ? asRecord(scenario.variant) : null;
  const incoming = presentation.edges.filter((edge) => edge.toId === node.id); const outgoing = presentation.edges.filter((edge) => edge.fromId === node.id);
  return <aside className="workflow-inspector" aria-label={`${node.label} evidence`}>
    <div className="inspector-heading"><div><span>{node.kind}</span><h3>{node.label}</h3></div><button type="button" className="text-button" onClick={onClose}>Close inspector</button></div>
    <p>{node.description}</p>
    <dl>
      {source && <><InspectorValue label="Arrival type" value={String(source.arrival?.type ?? "Unavailable")} /><InspectorValue label="Entry destination" value={source.firstStageId} /></>}
      {stage && <><InspectorValue label="Processing" value={JSON.stringify(stage.processingTime ?? {})} /><InspectorValue label="Resource" value={stage.resourcePoolId ? model?.resourcePools.find((item) => item.id === stage.resourcePoolId)?.name ?? stage.resourcePoolId : "Unavailable"} /><InspectorValue label="Incoming routes" value={incoming.map((item) => item.routeId).join(", ") || "None"} /><InspectorValue label="Outgoing routes" value={outgoing.map((item) => item.routeId).join(", ") || "None"} />{stage.failure && <InspectorValue label="Failure/rework" value={`${displayValue(stage.failure.probability)} probability; maximum ${displayValue(stage.failure.maximumReworkAttempts)} attempts`} />}</>}
      {resource && <><InspectorValue label="Capacity" value={displayValue(resource.capacity)} /><InspectorValue label="Supported stages" value={model?.stages.filter((item) => item.resourcePoolId === resource.id).map((item) => item.name ?? item.id).join(", ") || "None"} /></>}
      {node.kind === "terminal" && <><InspectorValue label="Terminal type" value="Completion" /><InspectorValue label="Incoming routes" value={incoming.map((item) => item.routeId).join(", ") || "None"} />{result && <><InspectorValue label="Baseline completion" value={formatEvidence("completionRate", systemMean(result.baseline, "completionRate"))} /><InspectorValue label="Scenario completion" value={formatEvidence("completionRate", systemMean(variant, "completionRate"))} /></>}</>}
      {change && <InspectorValue label="Explicit scenario change" value={changeLabel(change)} />}
      <InspectorValue label="Evidence status" value={result ? scenario?.status === "valid" ? "Valid scenario result" : "Scenario result unavailable" : "Comparison not run"} />
    </dl>
    {mode === "comparison" && comparisonMetrics.length > 0 && <table><caption>Baseline and scenario evidence</caption><thead><tr><th>Evidence</th><th>Baseline</th><th>Scenario</th><th>Delta</th></tr></thead><tbody>{comparisonMetrics.map((metric) => {
      const baselineValue = aggregate(result?.baseline, groupName, idKey, node.id, metric); const scenarioValue = aggregate(variant, groupName, idKey, node.id, metric);
      const deltaRecord = node.kind === "resource" && metric === "utilization" ? asRecord(asRecord(scenario?.resourceUtilizationDeltas)?.[node.id]) : null;
      const suppliedDelta = asRecord(deltaRecord?.absoluteDelta)?.mean; const delta = typeof suppliedDelta === "number" && Number.isFinite(suppliedDelta) ? suppliedDelta : null;
      return <tr key={metric}><th>{overlayOptions.find((item) => item.id === metric)?.label ?? metric}</th><td>{formatEvidence(metric, baselineValue)}</td><td>{formatEvidence(metric, scenarioValue)}</td><td>{delta === null ? "Unavailable" : metric === "utilization" ? `${(delta * 100).toFixed(1)} pp` : formatEvidence(metric, delta)}</td></tr>;
    })}</tbody></table>}
  </aside>;
}

function InspectorValue({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }
