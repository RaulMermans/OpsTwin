import { COLORS, decisionBriefText, formatMetric } from "./labState.js";

const COLUMNS = [
  { id: "baseline", label: "Human-only" },
  { id: "human-expansion", label: "Human expansion" },
  { id: "ai-assisted", label: "AI-assisted" },
  { id: "hybrid", label: "Hybrid" },
];

function byId(strategies, id) {
  return strategies?.find((item) => item.strategyId === id) ?? null;
}

function money(value, currency) {
  if (value == null || Number.isNaN(value)) return "unavailable";
  return `${formatMetric(value, 0)} ${currency}`;
}

function ratio(value) {
  if (value == null || Number.isNaN(value)) return "unavailable";
  return `${(value * 100).toFixed(1)}%`;
}

function payback(row) {
  if (!row) return "unavailable";
  if (row.paybackStatus === "no_payback") return "no payback";
  if (row.paybackStatus === "not_applicable") return "not applicable";
  if (row.paybackMonths == null) return "unavailable";
  return `${formatMetric(row.paybackMonths, 1)} months`;
}

function stateLabel(value) {
  return (value ?? "insufficient_evidence_for_a_decision").replaceAll("_", " ");
}

export function DecisionPanel({
  experiment,
  economics,
  assumptions,
  constraints,
  exploreParameter,
  onAssumptions,
  onConstraints,
  onEvaluate,
  onExplore,
  onExploreParameter,
}) {
  const currency = assumptions.currency;
  const strategies = economics.evidence?.strategies;
  const costs = (strategies ?? [])
    .map((item) => item.totalModeledCost)
    .filter((value) => Number.isFinite(value));
  const maxCost = Math.max(...costs, 1);
  const points = economics.evidence?.breakEven?.points ?? [];
  const maxAbs = Math.max(...points.map((item) => Math.abs(item.netBenefit ?? 0)), 1);

  return (
    <section>
      <h3>Economic assumptions</h3>
      <p>
        Synthetic demonstration defaults. These are not this organization&apos;s financial data. Changing only these
        values recomputes economics without rerunning the simulation.
      </p>
      <div className="grid">
        {[
          ["monthlyStaffCostPerFte", "Staff cost per FTE-month"],
          ["aiSubscriptionMonthly", "AI subscription / month"],
          ["aiCostPerAutomatedCase", "AI cost per automated case"],
          ["implementationCost", "Implementation expenditure"],
          ["evaluationMonths", "Evaluation months"],
          ["realizationRate", "Realization rate (0–1)"],
        ].map(([key, label]) => (
          <label key={key} className="stack">
            {label}
            <input
              type="number"
              min="0"
              step="any"
              value={assumptions[key]}
              onChange={(event) => onAssumptions({ [key]: Number(event.target.value) })}
            />
          </label>
        ))}
        <label className="stack">
          Realization mechanism
          <select
            value={assumptions.realizationMechanism}
            onChange={(event) => onAssumptions({ realizationMechanism: event.target.value })}
          >
            <option value="none">None — do not treat time savings as cash</option>
            <option value="avoided_hiring">Avoided hiring</option>
            <option value="reduced_overtime">Reduced overtime</option>
            <option value="reduced_outsourcing">Reduced outsourcing</option>
            <option value="realizable_payroll_reduction">Realizable payroll reduction</option>
          </select>
        </label>
        <label className="inline">
          <input
            type="checkbox"
            checked={assumptions.valueReleasedCapacity}
            onChange={(event) => onAssumptions({ valueReleasedCapacity: event.target.checked })}
          />
          Show theoretical value of released capacity (not cash)
        </label>
      </div>

      <h3>Decision constraints</h3>
      <div className="grid">
        {[
          ["maximumImplementationCost", "Max implementation"],
          ["maximumRecurringMonthly", "Max extra monthly spend"],
          ["maximumCycleTime", "Max cycle time (min)"],
          ["minimumCompletions", "Min completions"],
          ["maximumPaybackMonths", "Max payback (months)"],
        ].map(([key, label]) => (
          <label key={key} className="stack">
            {label}
            <input
              type="number"
              min="0"
              step="any"
              value={constraints[key]}
              onChange={(event) => onConstraints({ [key]: event.target.value })}
            />
          </label>
        ))}
      </div>

      <button className="primary" type="button" onClick={onEvaluate} disabled={economics.status === "running"}>
        {economics.status === "running" ? "Evaluating economics…" : "Evaluate investment"}
      </button>
      {economics.message ? (
        <p className={economics.status === "failed" ? "alert" : "status"} role={economics.status === "failed" ? "alert" : "status"}>
          {economics.message}
        </p>
      ) : null}
      {experiment.status === "stale" ? (
        <p className="status">Operational results are stale. Recalculate economics only after rerunning the experiment.</p>
      ) : null}

      {economics.evidence ? (
        <>
          <h3>Economic comparison</h3>
          <p>
            Measurement: {economics.evidence.measurementMode}. Completions are comparable. Throughput and utilization
            are not used as cash denominators. ROI is {economics.evidence.economicUncertainty.replaceAll("_", " ")}.
          </p>
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
                ["Operating expenditure", (row) => money(row?.existingOperatingExpenditure, currency)],
                ["Incremental AI expenditure", (row) => money(row?.incrementalAiCost, currency)],
                ["Implementation", (row) => money(row?.oneTimeImplementationExpenditure, currency)],
                ["Cost / successful case", (row) => money(row?.costPerSuccessfulCompletion, currency)],
                ["Released hours", (row) => (row?.releasedHumanHours == null ? "unavailable" : formatMetric(row.releasedHumanHours))],
                ["Realizable cash benefit", (row) => money(row?.realizableCashBenefit, currency)],
                ["Net benefit", (row) => money(row?.netBenefit, currency)],
                ["ROI", (row) => ratio(row?.roi)],
                ["Payback", payback],
                ["Decision", (row) => stateLabel(row?.decisionState)],
              ].map(([label, render]) => (
                <tr key={label}>
                  <td>{label}</td>
                  {COLUMNS.map((column) => (
                    <td key={column.id}>{render(byId(strategies, column.id))}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Cost versus cycle time</h3>
          {(strategies ?? [])
            .filter((item) => item.totalModeledCost != null && item.averageCycleTime != null)
            .map((item) => (
              <div className="bar-row" key={item.strategyId}>
                <span>{item.strategyId}</span>
                <div className="bar">
                  <span
                    style={{
                      width: `${(item.totalModeledCost / maxCost) * 100}%`,
                      background: COLORS[item.strategyId] ?? "#44546F",
                    }}
                  />
                </div>
                <span>
                  {money(item.totalModeledCost, currency)} / {formatMetric(item.averageCycleTime)} min
                </span>
              </div>
            ))}

          <h3>Break-even Explorer</h3>
          <p>Financial-only. Operational parameters such as coverage require a new simulation.</p>
          <label className="stack">
            Parameter
            <select value={exploreParameter} onChange={(event) => onExploreParameter(event.target.value)}>
              <option value="aiSubscriptionMonthly">AI subscription / month</option>
              <option value="implementationCost">Implementation expenditure</option>
              <option value="realizationRate">Realization rate</option>
              <option value="monthlyStaffCostPerFte">Staff cost per FTE-month</option>
              <option value="aiCostPerAutomatedCase">AI cost per automated case</option>
            </select>
          </label>
          <button className="secondary" type="button" onClick={onExplore} disabled={economics.status === "running"}>
            Evaluate break-even range
          </button>
          {economics.evidence.breakEven ? (
            <>
              <p>
                {economics.evidence.breakEven.explanation} Status:{" "}
                {economics.evidence.breakEven.thresholdStatus.replaceAll("_", " ")}
                {economics.evidence.breakEven.threshold != null
                  ? ` (about ${formatMetric(economics.evidence.breakEven.threshold, 2)})`
                  : ""}
                . Operational evidence was reused: {String(economics.evidence.breakEven.reusedOperationalEvidence)}.
              </p>
              <svg viewBox="0 0 320 120" width="100%" height="120" role="img" aria-label="Net benefit across the selected financial parameter">
                <line x1="20" y1="60" x2="300" y2="60" stroke="#dcdfe4" />
                {points.map((point, index) => {
                  const x = 20 + (index / Math.max(points.length - 1, 1)) * 280;
                  const y = 60 - ((point.netBenefit ?? 0) / maxAbs) * 50;
                  return <circle key={point.parameterValue} cx={x} cy={y} r="4" fill="#0c66e4" />;
                })}
              </svg>
            </>
          ) : null}

          <h3>Decision brief</h3>
          <pre className="brief">{decisionBriefText(economics.evidence.brief)}</pre>
        </>
      ) : (
        <p>Run a valid transformation experiment, then evaluate investment on that evidence.</p>
      )}
    </section>
  );
}
