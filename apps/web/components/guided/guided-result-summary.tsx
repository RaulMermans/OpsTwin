import type { ComparisonResult } from "../../lib/api/simulation";
import { buildComparativeInterpretation, type ComparativeInterpretation } from "../../lib/scenario-lab/comparative-interpretation";
import { directionAwareComparisonCopy, intervalInterpretationCopy, interpretReturnedInterval } from "../../lib/scenario-lab/guided-result-copy";
import { formatMetricDelta, guidedMetricLabel, type MetricKey } from "../../lib/scenario-lab/metrics";
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

function InterpretationStatement({ interpretation, direction }: { interpretation: ComparativeInterpretation; direction: string }) {
  const objective = interpretation.objectiveMetric as MetricKey;
  const label = guidedMetricLabel(objective);
  const metricPhrase = lowerLead(label);
  const note = excludedNote(interpretation.excludedCount, interpretation.totalCount);

  if (interpretation.kind === "noEligibleScenarios") {
    return <p className="comparative-interpretation">No tested scenario produced eligible paired evidence for {metricPhrase} in this experiment, so no comparison is available. {note}</p>;
  }

  if (interpretation.kind === "singleEligibleScenario") {
    return <p className="comparative-interpretation"><strong>{interpretation.scenarioName}</strong> was the only change with enough completed matched tests for {metricPhrase}, so there is no second change to compare. {intervalInterpretationCopy(interpretation.intervalKind)} {note}</p>;
  }

  if (interpretation.kind === "tie") {
    return <p className="comparative-interpretation">Among the tested scenarios, {interpretation.scenarioNames.join(" and ")} had the same observed average result for {metricPhrase} in this experiment. The displayed order uses the returned comparison order. {note}</p>;
  }

  return <p className="comparative-interpretation"><strong>{directionAwareComparisonCopy(interpretation.scenarioName, label, direction)}</strong> {intervalInterpretationCopy(interpretation.intervalKind)} {note}</p>;
}

export function GuidedResultSummary({ result, onNavigate }: Props) {
  const objective = String(asRecord(result.objective)?.metric ?? "averageCycleTime") as MetricKey;
  const direction = String(asRecord(result.objective)?.direction ?? "minimize");
  const label = guidedMetricLabel(objective);
  const interpretation = buildComparativeInterpretation(result);
  return <section className="guided-result" aria-labelledby="guided-result-title">
    <p className="eyebrow">Observed result</p><h2 id="guided-result-title">Comparison complete</h2>
    <p>Primary measure: <strong>{label}</strong>. {direction === "minimize" ? "Lower values indicate improvement for this measure." : "Higher values indicate improvement for this measure."}</p>
    <div className="guided-result-cards">{asRecords(result.scenarios).map((scenario) => {
      const paired = pairedMetric(scenario, objective); const delta = asRecord(paired?.absoluteDelta)?.mean;
      const improvementRecord = asRecord(paired?.improvement);
      const improvement = improvementRecord?.probabilityOfImprovement;
      const improvedCount = improvementRecord?.improvedCount;
      const pairedCount = improvementRecord?.validPairedRunCount ?? scenario.pairedRunCount;
      const interval = confidence(paired);
      const intervalEvidence = interval && typeof interval.lower === "number" && typeof interval.upper === "number" ? { lower: interval.lower, upper: interval.upper } : null;
      const intervalKind = interpretReturnedInterval(intervalEvidence, direction);
      const averageDifference = formatMetricDelta(objective, delta);
      return <article key={String(scenario.scenarioId)}><h3>{String(scenario.scenarioName ?? scenario.scenarioId)}</h3><p>Average change: <strong>{averageDifference}</strong>.</p><p>Better in <strong>{typeof improvedCount === "number" && typeof pairedCount === "number" && typeof improvement === "number" ? `${improvedCount} of ${pairedCount} matched tests (${(improvement * 100).toFixed(0)}%)` : "an unavailable number of matched tests"}</strong>.</p><p className="hint">Plausible range of the average change: {intervalEvidence ? `${formatMetricDelta(objective, intervalEvidence.lower)} to ${formatMetricDelta(objective, intervalEvidence.upper)}` : "not available"}.</p><p className="hint">{intervalInterpretationCopy(intervalKind)}</p></article>;
    })}</div>
    <InterpretationStatement interpretation={interpretation} direction={direction} />
    <p className="guided-disclaimer">{NON_PRESCRIPTIVE_DISCLAIMER}</p>
    <details className="guided-result-help"><summary>How to read this result</summary><dl><div><dt>Average difference</dt><dd>The average difference across all matched simulated operating days.</dd></div><div><dt>How often it performed better</dt><dd>The percentage of matched simulations where the proposed change beat the current operation.</dd></div><div><dt>Plausible range</dt><dd>The range of average effects supported by this experiment.</dd></div><div><dt>Inconclusive</dt><dd>The experiment did not show a stable direction because the plausible range includes no improvement or a worse result.</dd></div></dl></details>
    <nav className="guided-evidence-nav" aria-label="Evidence navigation">
      <button type="button" onClick={() => onNavigate("flow-evidence")}>See where the process changed</button>
      <button type="button" onClick={() => onNavigate("risk-evidence")}>Inspect uncertainty and risk</button>
      <button type="button" onClick={() => onNavigate("economics-evidence")}>Add operating costs</button>
      <button type="button" onClick={() => onNavigate("playback-evidence")}>Watch a representative run</button>
      <button type="button" onClick={() => onNavigate("technical-evidence")}>View technical evidence</button>
    </nav>
  </section>;
}
