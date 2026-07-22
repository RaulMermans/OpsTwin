import type { ComparisonResult } from "../api/simulation";
import { interpretReturnedInterval, type IntervalInterpretation } from "./guided-result-copy";
import type { MetricKey } from "./metrics";
import { asRecord, asRecords, confidence, pairedMetric, type UnknownRecord } from "./result-adapter";

// Mirrors the centralized comparison tolerance documented in docs/SCENARIO_COMPARISON_SPEC.md
// (apps/simulation-api/app/scenarios/metrics.py FLOAT_COMPARISON_TOLERANCE). Used only to describe
// an existing ranking outcome as a tie for presentation; it never recomputes ranking order.
export const TIE_TOLERANCE = 1e-9;

export type ComparativeInterpretation =
  | { kind: "noEligibleScenarios"; objectiveMetric: string; excludedCount: number; totalCount: number }
  | {
      kind: "singleEligibleScenario";
      objectiveMetric: string;
      excludedCount: number;
      totalCount: number;
      scenarioId: string;
      scenarioName: string;
      objectiveMeanDelta: number;
      probabilityOfImprovement: number;
      intervalKind: IntervalInterpretation;
    }
  | {
      kind: "tie";
      objectiveMetric: string;
      excludedCount: number;
      totalCount: number;
      scenarioIds: string[];
      scenarioNames: string[];
      objectiveMeanDelta: number;
      tieBreakExplanation: string;
    }
  | {
      kind: "leader";
      objectiveMetric: string;
      excludedCount: number;
      totalCount: number;
      scenarioId: string;
      scenarioName: string;
      objectiveMeanDelta: number;
      probabilityOfImprovement: number;
      intervalKind: IntervalInterpretation;
    };

function scenarioNameFor(scenarios: UnknownRecord[], id: string): string {
  const match = scenarios.find((item) => item.scenarioId === id);
  return match ? String(match.scenarioName ?? match.scenarioId) : id;
}

function intervalKindFor(scenarios: UnknownRecord[], scenarioId: string, objectiveMetric: string, direction: string): IntervalInterpretation {
  const scenario = scenarios.find((item) => item.scenarioId === scenarioId);
  if (!scenario) return "unavailable";
  const paired = pairedMetric(scenario, objectiveMetric as MetricKey);
  const interval = confidence(paired);
  const evidence = interval && typeof interval.lower === "number" && typeof interval.upper === "number" ? { lower: interval.lower, upper: interval.upper } : null;
  return interpretReturnedInterval(evidence, direction);
}

/**
 * Derives a factual, direction-aware Guided comparison statement from an existing
 * scenario-comparison response. Reads the backend's own ranking order and tie-break
 * explanation; it does not recompute eligibility, deltas, or rank order.
 */
export function buildComparativeInterpretation(result: ComparisonResult): ComparativeInterpretation {
  const objectiveMetric = String(asRecord(result.objective)?.metric ?? "");
  const direction = String(asRecord(result.objective)?.direction ?? "minimize");
  const scenarios = asRecords(result.scenarios);
  const totalCount = scenarios.length;
  const ranking = asRecords(result.ranking)
    .slice()
    .sort((a, b) => (Number(a.rank) || 0) - (Number(b.rank) || 0));
  const excludedCount = totalCount - ranking.length;

  if (ranking.length === 0) {
    return { kind: "noEligibleScenarios", objectiveMetric, excludedCount, totalCount };
  }

  if (ranking.length === 1) {
    const only = ranking[0];
    const scenarioId = String(only.scenarioId);
    return {
      kind: "singleEligibleScenario",
      objectiveMetric,
      excludedCount,
      totalCount,
      scenarioId,
      scenarioName: scenarioNameFor(scenarios, scenarioId),
      objectiveMeanDelta: Number(only.objectiveMeanDelta),
      probabilityOfImprovement: Number(only.probabilityOfImprovement),
      intervalKind: intervalKindFor(scenarios, scenarioId, objectiveMetric, direction),
    };
  }

  const [first, second] = ranking;
  const firstDelta = Number(first.objectiveMeanDelta);
  const secondDelta = Number(second.objectiveMeanDelta);

  if (Math.abs(firstDelta - secondDelta) <= TIE_TOLERANCE) {
    const tied = ranking.filter((row) => Math.abs(Number(row.objectiveMeanDelta) - firstDelta) <= TIE_TOLERANCE);
    const scenarioIds = tied.map((row) => String(row.scenarioId));
    return {
      kind: "tie",
      objectiveMetric,
      excludedCount,
      totalCount,
      scenarioIds,
      scenarioNames: scenarioIds.map((id) => scenarioNameFor(scenarios, id)),
      objectiveMeanDelta: firstDelta,
      tieBreakExplanation: String(first.tieBreakExplanation ?? ""),
    };
  }

  const scenarioId = String(first.scenarioId);
  return {
    kind: "leader",
    objectiveMetric,
    excludedCount,
    totalCount,
    scenarioId,
    scenarioName: scenarioNameFor(scenarios, scenarioId),
    objectiveMeanDelta: firstDelta,
    probabilityOfImprovement: Number(first.probabilityOfImprovement),
    intervalKind: intervalKindFor(scenarios, scenarioId, objectiveMetric, direction),
  };
}
