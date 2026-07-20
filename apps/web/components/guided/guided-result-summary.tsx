import type { ComparisonResult } from "../../lib/api/simulation";
import { formatMetric, metricRegistry, type MetricKey } from "../../lib/scenario-lab/metrics";
import { asRecord, asRecords, confidence, pairedMetric } from "../../lib/scenario-lab/result-adapter";

type Props = { result: ComparisonResult; onNavigate: (target: string) => void };

export function GuidedResultSummary({ result, onNavigate }: Props) {
  const objective = String(asRecord(result.objective)?.metric ?? "averageCycleTime") as MetricKey;
  const direction = String(asRecord(result.objective)?.direction ?? "minimize");
  const label = metricRegistry[objective]?.label ?? objective;
  return <section className="guided-result" aria-labelledby="guided-result-title">
    <p className="eyebrow">Observed result</p><h2 id="guided-result-title">Comparison complete</h2>
    <p>Primary measure: <strong>{label}</strong>. {direction === "minimize" ? "Lower values indicate improvement for this measure." : "Higher values indicate improvement for this measure."}</p>
    <div className="guided-result-cards">{asRecords(result.scenarios).map((scenario) => {
      const paired = pairedMetric(scenario, objective); const delta = asRecord(paired?.absoluteDelta)?.mean;
      const improvement = asRecord(paired?.improvement)?.probabilityOfImprovement;
      const interval = confidence(paired);
      return <article key={String(scenario.scenarioId)}><h3>{String(scenario.scenarioName ?? scenario.scenarioId)}</h3><p>{label} changed by <strong>{formatMetric(objective, delta)}</strong>.</p><p>It improved against the baseline in <strong>{typeof improvement === "number" ? `${(improvement * 100).toFixed(0)}%` : "an unavailable proportion"}</strong> of paired simulations.</p><p className="hint">Uncertainty around the estimated average: {interval ? `${formatMetric(objective, interval.lower)} to ${formatMetric(objective, interval.upper)}` : "not available"}.</p></article>;
    })}</div>
    <p className="guided-disclaimer">This is comparative simulation evidence, not a recommendation.</p>
    <nav className="guided-evidence-nav" aria-label="Evidence navigation">
      <button type="button" onClick={() => onNavigate("flow-evidence")}>See where queues changed</button>
      <button type="button" onClick={() => onNavigate("risk-evidence")}>Inspect uncertainty and risk</button>
      <button type="button" onClick={() => onNavigate("economics-evidence")}>Add operating costs</button>
      <button type="button" onClick={() => onNavigate("playback-evidence")}>Watch a representative run</button>
      <button type="button" onClick={() => onNavigate("technical-evidence")}>View technical evidence</button>
    </nav>
  </section>;
}
