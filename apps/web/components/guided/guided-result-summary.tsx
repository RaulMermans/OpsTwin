import type { ComparisonResult } from "../../lib/api/simulation";
import { buildComparativeInterpretation, type ComparativeInterpretation } from "../../lib/scenario-lab/comparative-interpretation";
import { formatMetric, metricRegistry, type MetricKey } from "../../lib/scenario-lab/metrics";
import { asRecord, asRecords, confidence, pairedMetric } from "../../lib/scenario-lab/result-adapter";

type Props = { result: ComparisonResult; onNavigate: (target: string) => void };

const NON_PRESCRIPTIVE_DISCLAIMER = "This is comparative simulation evidence, not a recommendation.";

// Mid-sentence casing only; leaves acronym/leading-digit labels (e.g. "SLA attainment", "P95 cycle time") untouched.
function lowerLead(label: string): string {
  const [first, ...rest] = label.split(" ");
  if (!first || first === first.toUpperCase()) return label;
  return [first.charAt(0).toLowerCase() + first.slice(1), ...rest].join(" ");
}

function excludedNote(excludedCount: number, totalCount: number): string | null {
  if (excludedCount <= 0) return null;
  return `${excludedCount} of ${totalCount} tested scenario${totalCount === 1 ? "" : "s"} failed or was ineligible and ${excludedCount === 1 ? "is" : "are"} excluded from this comparison.`;
}

function InterpretationStatement({ interpretation }: { interpretation: ComparativeInterpretation }) {
  const objective = interpretation.objectiveMetric as MetricKey;
  const label = metricRegistry[objective]?.label ?? interpretation.objectiveMetric;
  const metricPhrase = lowerLead(label);
  const note = excludedNote(interpretation.excludedCount, interpretation.totalCount);

  if (interpretation.kind === "noEligibleScenarios") {
    return <p className="comparative-interpretation">No tested scenario produced eligible paired evidence for {metricPhrase} in this experiment, so no comparison is available. {note}</p>;
  }

  if (interpretation.kind === "singleEligibleScenario") {
    return <p className="comparative-interpretation"><strong>{interpretation.scenarioName}</strong> was the only tested scenario with eligible paired evidence for {metricPhrase} in this experiment (observed mean change {formatMetric(objective, interpretation.objectiveMeanDelta)}, improved in {(interpretation.probabilityOfImprovement * 100).toFixed(0)}% of paired simulations); there is no second eligible scenario to compare it against. {note}</p>;
  }

  if (interpretation.kind === "tie") {
    return <p className="comparative-interpretation">Among the tested scenarios, {interpretation.scenarioNames.join(" and ")} produced a statistically equivalent observed change in {metricPhrase} in this experiment (observed mean change {formatMetric(objective, interpretation.objectiveMeanDelta)}; tie-broken deterministically by {interpretation.tieBreakExplanation}). {note}</p>;
  }

  return <p className="comparative-interpretation">Among the tested scenarios, <strong>{interpretation.scenarioName}</strong> produced the larger observed improvement in {metricPhrase} in this experiment (observed mean change {formatMetric(objective, interpretation.objectiveMeanDelta)}, improved in {(interpretation.probabilityOfImprovement * 100).toFixed(0)}% of paired simulations). {note}</p>;
}

export function GuidedResultSummary({ result, onNavigate }: Props) {
  const objective = String(asRecord(result.objective)?.metric ?? "averageCycleTime") as MetricKey;
  const direction = String(asRecord(result.objective)?.direction ?? "minimize");
  const label = metricRegistry[objective]?.label ?? objective;
  const interpretation = buildComparativeInterpretation(result);
  return <section className="guided-result" aria-labelledby="guided-result-title">
    <p className="eyebrow">Observed result</p><h2 id="guided-result-title">Comparison complete</h2>
    <p>Primary measure: <strong>{label}</strong>. {direction === "minimize" ? "Lower values indicate improvement for this measure." : "Higher values indicate improvement for this measure."}</p>
    <div className="guided-result-cards">{asRecords(result.scenarios).map((scenario) => {
      const paired = pairedMetric(scenario, objective); const delta = asRecord(paired?.absoluteDelta)?.mean;
      const improvement = asRecord(paired?.improvement)?.probabilityOfImprovement;
      const interval = confidence(paired);
      return <article key={String(scenario.scenarioId)}><h3>{String(scenario.scenarioName ?? scenario.scenarioId)}</h3><p>{label} changed by <strong>{formatMetric(objective, delta)}</strong>.</p><p>It improved against the baseline in <strong>{typeof improvement === "number" ? `${(improvement * 100).toFixed(0)}%` : "an unavailable proportion"}</strong> of paired simulations.</p><p className="hint">Uncertainty around the estimated average: {interval ? `${formatMetric(objective, interval.lower)} to ${formatMetric(objective, interval.upper)}` : "not available"}.</p></article>;
    })}</div>
    <InterpretationStatement interpretation={interpretation} />
    <p className="guided-disclaimer">{NON_PRESCRIPTIVE_DISCLAIMER}</p>
    <nav className="guided-evidence-nav" aria-label="Evidence navigation">
      <button type="button" onClick={() => onNavigate("flow-evidence")}>See where queues changed</button>
      <button type="button" onClick={() => onNavigate("risk-evidence")}>Inspect uncertainty and risk</button>
      <button type="button" onClick={() => onNavigate("economics-evidence")}>Add operating costs</button>
      <button type="button" onClick={() => onNavigate("playback-evidence")}>Watch a representative run</button>
      <button type="button" onClick={() => onNavigate("technical-evidence")}>View technical evidence</button>
    </nav>
  </section>;
}
