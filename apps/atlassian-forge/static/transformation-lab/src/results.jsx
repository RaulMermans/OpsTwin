import { operationalInsights } from "./insights.js";
import { COLORS, formatInterval, formatMetric } from "./labState.js";

const COLUMNS = [
  { id: "baseline", label: "Baseline" },
  { id: "human-expansion", label: "Human expansion" },
  { id: "ai-assisted", label: "AI-assisted" },
  { id: "hybrid", label: "Hybrid" },
];

function byId(evidence, id) {
  return evidence.alternatives?.find((item) => item.alternativeId === id) ?? null;
}

function cell(metric) {
  return metric?.mean == null ? "unavailable" : formatMetric(metric.mean);
}

function delta(base, scenario) {
  if (base?.mean == null || scenario?.mean == null) return "";
  const change = scenario.mean - base.mean;
  const sign = change > 0 ? "+" : "";
  return ` (${sign}${formatMetric(change)})`;
}

function stageMean(source, stageId, metricId) {
  return source?.[stageId]?.[metricId];
}

function utilColor(value) {
  if (value == null) return "#f7f8f9";
  if (value >= 0.85) return "#ffeceb";
  if (value >= 0.65) return "#fff7d6";
  return "#f7f8f9";
}

export function ResultsPanel({ evidence, transform }) {
  if (!evidence) {
    return <p>Run a transformation experiment to populate this workspace.</p>;
  }
  const insights = operationalInsights(evidence);
  const cycleValues = [
    evidence.baselineMetrics?.averageCycleTime?.mean,
    ...COLUMNS.slice(1).map((column) => byId(evidence, column.id)?.systemMetrics?.averageCycleTime?.mean),
  ].filter((value) => Number.isFinite(value));
  const maxCycle = Math.max(...cycleValues, 1);
  const stages = ["triage", "resolution"];

  return (
    <section>
      {evidence.experimentStatus === "partial" ? (
        <p className="status" role="status">
          Partial experiment. At least one alternative failed and is not shown as a successful result.
        </p>
      ) : null}
      {evidence.experimentStatus === "failed" ? (
        <p className="alert" role="alert">The experiment did not produce a complete comparison.</p>
      ) : null}
      {evidence.exploratory ? (
        <p className="status">Exploratory evidence. This is not a historically validated forecast of OPS.</p>
      ) : null}

      <h3>Comparative summary</h3>
      <p>Values are simulation outputs. Parentheses are baseline-relative differences. No alternative is ranked as universally best.</p>
      <table className="compare">
        <thead>
          <tr>
            <th>Metric</th>
            {COLUMNS.map((column) => (
              <th key={column.id}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[
            ["Average cycle time (min)", "averageCycleTime", null],
            ["Throughput (items/min)", "completionRate", null],
            ["Successful completions", "completedItems", null],
            ["Unsuccessful outcomes", "terminallyFailedItems", null],
            ["SLA attainment", "slaAttainment", null],
          ].map(([label, key]) => (
            <tr key={key}>
              <td>{label}</td>
              <td>{cell(evidence.baselineMetrics?.[key])}</td>
              {COLUMNS.slice(1).map((column) => {
                const alternative = byId(evidence, column.id);
                if (!alternative) return <td key={column.id}>not in experiment</td>;
                if (alternative.status !== "valid") return <td key={column.id}>failed</td>;
                return (
                  <td key={column.id}>
                    {cell(alternative.systemMetrics?.[key])}
                    {key === "averageCycleTime" ? delta(evidence.baselineMetrics?.[key], alternative.systemMetrics?.[key]) : ""}
                  </td>
                );
              })}
            </tr>
          ))}
          {stages.map((stageId) => (
            <tr key={`${stageId}-wait`}>
              <td>{stageId} waiting (min)</td>
              <td>{cell(stageMean(evidence.baselineStageMetrics, stageId, "averageWaitingTime"))}</td>
              {COLUMNS.slice(1).map((column) => {
                const alternative = byId(evidence, column.id);
                if (!alternative || alternative.status !== "valid") {
                  return <td key={column.id}>{alternative ? "failed" : "not in experiment"}</td>;
                }
                return <td key={column.id}>{cell(stageMean(alternative.stageMetrics, stageId, "averageWaitingTime"))}</td>;
              })}
            </tr>
          ))}
          <tr>
            <td>Resolution utilization</td>
            <td>{cell(evidence.baselineResourceMetrics?.["resolution-team"]?.utilization)}</td>
            {COLUMNS.slice(1).map((column) => {
              const alternative = byId(evidence, column.id);
              if (!alternative || alternative.status !== "valid") {
                return <td key={column.id}>{alternative ? "failed" : "not in experiment"}</td>;
              }
              return <td key={column.id}>{cell(alternative.resourceMetrics?.["resolution-team"]?.utilization)}</td>;
            })}
          </tr>
        </tbody>
      </table>

      <h3>Cycle-time comparison</h3>
      <p>Bars use average cycle time in minutes. Caps show 95% intervals on the mean of run averages where returned.</p>
      {[
        { id: "baseline", label: "Baseline", metric: evidence.baselineMetrics?.averageCycleTime },
        ...COLUMNS.slice(1).map((column) => ({
          id: column.id,
          label: column.label,
          metric: byId(evidence, column.id)?.status === "valid" ? byId(evidence, column.id).systemMetrics?.averageCycleTime : null,
        })),
      ].map((row) => (
        <div className="bar-row" key={row.id}>
          <span>{row.label}</span>
          <div className="bar" aria-hidden="true">
            <span
              style={{
                width: `${row.metric?.mean ? Math.min(100, (row.metric.mean / maxCycle) * 100) : 0}%`,
                background: COLORS[row.id] ?? COLORS.baseline,
              }}
            />
          </div>
          <span>
            {cell(row.metric)}
            {row.metric?.lower != null ? ` [${formatMetric(row.metric.lower)}–${formatMetric(row.metric.upper)}]` : ""}
          </span>
        </div>
      ))}

      <h3>Stage pressure</h3>
      <p>Intake is the arrival source. Pressure uses time-weighted queue length from the engine, not status residence.</p>
      <div className="pipeline">
        {["arrivals", "triage", "resolution", "completion"].map((stageId) => (
          <div className="stage" key={stageId}>
            <strong>{stageId}</strong>
            {stageId === "arrivals" || stageId === "completion" ? (
              <p>Not a queued stage in this model.</p>
            ) : (
              COLUMNS.map((column) => {
                const source =
                  column.id === "baseline"
                    ? evidence.baselineStageMetrics
                    : byId(evidence, column.id)?.status === "valid"
                      ? byId(evidence, column.id).stageMetrics
                      : null;
                return (
                  <p key={column.id}>
                    {column.label}: {cell(stageMean(source, stageId, "timeWeightedQueueLength"))}
                  </p>
                );
              })
            )}
          </div>
        ))}
      </div>

      <h3>Resource utilization</h3>
      <p>High utilization is not automatically a bottleneck. Compare waiting time before treating saturation as congestion.</p>
      {["triage-team", "resolution-team"].map((pool) => (
        <div className="heat" key={pool}>
          <span>{pool}</span>
          {["baseline", ...COLUMNS.slice(1).map((column) => column.id)].map((id) => {
            const metric =
              id === "baseline"
                ? evidence.baselineResourceMetrics?.[pool]?.utilization
                : byId(evidence, id)?.resourceMetrics?.[pool]?.utilization;
            return (
              <b key={id} style={{ background: utilColor(metric?.mean) }}>
                {id}: {cell(metric)}
              </b>
            );
          })}
        </div>
      ))}

      <h3>Uncertainty</h3>
      <dl>
        <dt>Replications requested</dt>
        <dd>{evidence.experiment?.runCount} paired runs ({evidence.experiment?.runCount < 8 ? "exploratory sample" : "lab sample"})</dd>
        <dt>Integrity</dt>
        <dd>{evidence.integrityStatus ?? "unavailable"}</dd>
        <dt>Experiment status</dt>
        <dd>{evidence.experimentStatus}</dd>
      </dl>
      <table className="compare">
        <thead>
          <tr>
            <th>Alternative</th>
            <th>Paired cycle-time CI</th>
            <th>Improvement frequency</th>
            <th>Valid pairs</th>
          </tr>
        </thead>
        <tbody>
          {(evidence.alternatives ?? []).map((alternative) => (
            <tr key={alternative.alternativeId}>
              <td>{alternative.interventionName}</td>
              <td>{alternative.status === "valid" ? formatInterval(alternative.pairedCycleTime) : alternative.message}</td>
              <td>{alternative.probabilityOfImprovement == null ? "unavailable" : formatMetric(alternative.probabilityOfImprovement)}</td>
              <td>{alternative.validPairedRunCount ?? "unavailable"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>{evidence.improvementInterpretation}</p>

      <h3>Operational observations</h3>
      {insights.length === 0 ? (
        <p>No deterministic observation met the evidence thresholds.</p>
      ) : (
        <ul>
          {insights.map((item) => (
            <li key={item.text}>{item.text}</li>
          ))}
        </ul>
      )}

      <details>
        <summary>Technical evidence</summary>
        <dl>
          <dt>Baseline class</dt>
          <dd>{evidence.baselineClass}{evidence.exploratory ? " (exploratory)" : ""}</dd>
          <dt>Fixture</dt>
          <dd>{evidence.fixtureId}</dd>
          <dt>Experiment id</dt>
          <dd>{evidence.experimentId}</dd>
          <dt>Model fingerprint</dt>
          <dd>{evidence.calibratedModelFingerprint}</dd>
          <dt>Comparison hash</dt>
          <dd>{evidence.comparisonBaselineHash ?? "not executed"}</dd>
          <dt>Demand volume</dt>
          <dd>{evidence.experiment?.itemCount} items, seed {evidence.experiment?.baseSeed}</dd>
          <dt>Approximations</dt>
          <dd>{(evidence.approximations ?? []).join(", ") || "none"}</dd>
        </dl>
        <ul>
          {(evidence.disclosures ?? []).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p>Current configuration: {transform.itemCount} items × {transform.runCount} replications. Refreshing Jira discards this session.</p>
      </details>
    </section>
  );
}
