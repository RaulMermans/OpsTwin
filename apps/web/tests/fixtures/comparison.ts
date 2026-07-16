import type { ComparisonResult } from "../../lib/api/simulation";

const aggregate = (mean: number) => ({ count: 10, mean, sampleVariance: 1, standardDeviation: 1, minimum: mean - 1, maximum: mean + 1, p10: mean - 1, p50: mean, p90: mean + 1, confidenceInterval: { level: 0.95, lower: mean - 0.5, upper: mean + 0.5, method: "normal_approximation", successfulRunCount: 10, reliableSampleSize: false } });
const systemMetrics = { slaAttainment: aggregate(0.82), averageWaitingTime: aggregate(4), averageCycleTime: aggregate(24), p95CycleTime: aggregate(40), timeWeightedWip: aggregate(9), timeWeightedQueueLength: aggregate(3), completionRate: aggregate(0.6), terminalFailureRate: aggregate(0.03), flowEfficiency: aggregate(0.7), totalReworkCount: aggregate(8) };
const paired = (mean: number) => ({ metric: "averageCycleTime", absoluteDelta: aggregate(mean), relativeDelta: aggregate(mean / 24), relativeDeltaUndefinedCount: 0, improvement: { improvedCount: 8, degradedCount: 1, tiedCount: 1, probabilityOfImprovement: 0.8, probabilityOfDegradation: 0.1, probabilityOfTie: 0.1, validPairedRunCount: 10 } });
const resource = (id: string, utilization: number) => ({ resourcePoolId: id, metrics: { utilization: aggregate(utilization), idleCapacityProportion: aggregate(1 - utilization), meanRequestWait: aggregate(2), maximumConcurrentUsage: aggregate(3), totalRequests: aggregate(100) } });
const stage = (id: string, waiting: number, queue: number, failure: number, rework: number, visits: number) => ({ stageId: id, metrics: { averageWaitingTime: aggregate(waiting), timeWeightedQueueLength: aggregate(queue), failureRate: aggregate(failure), reworkCount: aggregate(rework), visitCount: aggregate(visits) } });
const baselineStages = [stage("triage", 4, 3, 0, 0, 100), stage("level-1", 6, 5, 0, 0, 80), stage("level-2", 9, 7, 0, 0, 30), stage("quality-check", 3, 2, 0.1, 8, 110)];
const scenarioStages = [stage("triage", 4, 3, 0, 0, 100), stage("level-1", 4, 3, 0, 0, 80), stage("level-2", 8, 6, 0, 0, 30), stage("quality-check", 3, 2, 0.1, 8, 110)];
const baselineResources = [resource("triage-team", 0.68), resource("level-1-agents", 0.7), resource("level-2-agents", 0.76), resource("quality-team", 0.64)];
const scenarioResources = [resource("triage-team", 0.68), resource("level-1-agents", 0.62), resource("level-2-agents", 0.75), resource("quality-team", 0.64)];

export const comparisonFixture = {
  schemaVersion: "0.5.0",
  baselineModelHash: "a".repeat(64),
  requestedRunCount: 10,
  confidenceLevel: 0.95,
  baseline: { systemMetrics, stageMetrics: baselineStages, resourcePoolMetrics: baselineResources },
  scenarios: [{
    scenarioId: "scenario-1", scenarioName: "Add one Level 1 agent", status: "valid", failure: null, scenarioModelHash: "b".repeat(64), appliedOverrideCount: 1,
    appliedOverrides: [{ entityId: "level-1-agents", field: "capacity", previousValue: 4, value: 5 }], requestedRunCount: 10, scenarioSuccessfulRunCount: 10, pairedRunCount: 10,
    pairedMetrics: Object.fromEntries(Object.keys(systemMetrics).map((key) => [key, paired(key === "averageCycleTime" ? -2 : 0.01)])),
    variant: { systemMetrics: { ...systemMetrics, averageCycleTime: aggregate(22) }, stageMetrics: scenarioStages, resourcePoolMetrics: scenarioResources },
    resourceUtilizationDeltas: { "level-1-agents": { absoluteDelta: aggregate(-0.08), relativeDelta: aggregate(-0.11), relativeDeltaUndefinedCount: 0 } },
    riskComparisons: [{ metric: "averageCycleTime", threshold: 60, baselineProbability: 0.2, scenarioProbability: 0.1, probabilityPointChange: -0.1, baselineOnlyViolates: 2, scenarioOnlyViolates: 1, bothViolate: 0, neitherViolates: 7, pairedRunCount: 10 }],
    guardrails: [{ metric: "slaAttainment", operator: "greaterThanOrEqual", threshold: 0.75, observedValue: 0.82, passed: true }], eligible: true,
  }],
  ranking: [{ scenarioId: "scenario-1", rank: 1, eligible: true, guardrailsPassed: true, objectiveMetric: "averageCycleTime", objectiveMeanDelta: -2, probabilityOfImprovement: 0.8, confidenceIntervalWidth: 1 }],
  objective: { metric: "averageCycleTime", direction: "minimize" },
  representatives: { baseline: null, scenario: { variantId: "scenario-1", representative: { seed: 42 } } },
  workBudget: { estimatedWorkUnits: 2000 },
  execution: { executionOrder: "run_index_then_baseline_then_scenarios", ordinaryRunRetainedEventCount: 0 },
  integrity: { status: "passed", checksRun: 16 },
} as unknown as ComparisonResult;
