const LABELS = {
  "human-expansion": "human capacity expansion",
  "ai-assisted": "AI-assisted processing",
  hybrid: "hybrid automation",
};

function mean(metric) {
  return metric && Number.isFinite(metric.mean) ? metric.mean : null;
}

function relativeChange(base, scenario) {
  if (base == null || scenario == null || Math.abs(base) < 1e-9) return null;
  return (scenario - base) / Math.abs(base);
}

function stageWait(evidence, alternative, stageId) {
  const base = mean(evidence.baselineStageMetrics?.[stageId]?.averageWaitingTime);
  const next = mean(alternative.stageMetrics?.[stageId]?.averageWaitingTime);
  return { base, next, change: relativeChange(base, next) };
}

export function operationalInsights(evidence) {
  if (!evidence || evidence.experimentStatus === "failed") return [];
  const insights = [];
  const cycleBase = mean(evidence.baselineMetrics?.averageCycleTime);
  for (const alternative of evidence.alternatives ?? []) {
    if (alternative.status !== "valid") continue;
    const name = LABELS[alternative.alternativeId] ?? alternative.interventionName;
    const cycle = mean(alternative.systemMetrics?.averageCycleTime);
    const cycleChange = relativeChange(cycleBase, cycle);
    const frequency = alternative.probabilityOfImprovement;
    const interval = alternative.pairedCycleTime;
    const uncertain =
      interval &&
      Number.isFinite(interval.lower) &&
      Number.isFinite(interval.upper) &&
      interval.lower <= 0 &&
      interval.upper >= 0;
    if (uncertain || (frequency != null && frequency > 0.2 && frequency < 0.8)) {
      insights.push({
        category: "uncertain-improvement",
        text: `${name}: cycle-time change is uncertain under the selected replications (improvement frequency ${
          frequency == null ? "unavailable" : frequency.toFixed(2)
        }; paired difference CI ${
          interval ? `${interval.lower.toFixed(2)} to ${interval.upper.toFixed(2)} minutes` : "unavailable"
        }).`,
      });
    } else if (cycleChange != null && Math.abs(cycleChange) >= 0.03) {
      insights.push({
        category: cycleChange < 0 ? "cycle-time-improvement" : "no-cycle-time-gain",
        text: `${name}: average cycle time ${cycleChange < 0 ? "decreases" : "increases"} by ${(
          Math.abs(cycleChange) * 100
        ).toFixed(1)}% relative to the human-only baseline.`,
      });
    } else if (cycleChange != null) {
      insights.push({
        category: "no-meaningful-difference",
        text: `${name}: average cycle time does not differ meaningfully from baseline under these assumptions.`,
      });
    }
    const triage = stageWait(evidence, alternative, "triage");
    const resolution = stageWait(evidence, alternative, "resolution");
    if (triage.change != null && resolution.change != null && triage.change <= -0.05 && resolution.change >= 0.05) {
      insights.push({
        category: "downstream-queue-pressure",
        text: `${name} reduces average triage waiting time, while resolution waiting increases under the selected demand assumptions.`,
      });
    }
    const util = mean(alternative.resourceMetrics?.["resolution-team"]?.utilization);
    const baseUtil = mean(evidence.baselineResourceMetrics?.["resolution-team"]?.utilization);
    if (util != null && util >= 0.85 && resolution.change != null && resolution.change > 0.05) {
      insights.push({
        category: "resource-saturation",
        text: `${name}: resolution-team utilization is ${(util * 100).toFixed(0)}% with higher resolution waiting. High utilization is not classified as a bottleneck without that waiting-time evidence.`,
      });
    }
    const throughput = mean(alternative.systemMetrics?.completionRate);
    const baseThroughput = mean(evidence.baselineMetrics?.completionRate);
    const throughputChange = relativeChange(baseThroughput, throughput);
    if (throughputChange != null && throughputChange <= -0.05 && cycleChange != null && cycleChange < 0) {
      insights.push({
        category: "throughput-limitation",
        text: `${name}: cycle time improved while throughput did not increase. Completing work faster did not raise completions per minute under this demand.`,
      });
    }
    const failed = mean(alternative.systemMetrics?.terminallyFailedItems);
    const baseFailed = mean(evidence.baselineMetrics?.terminallyFailedItems);
    if (failed != null && baseFailed != null && failed > baseFailed + 0.05) {
      insights.push({
        category: "unsuccessful-outcomes",
        text: `${name} increases unsuccessful outcomes relative to the human-only baseline.`,
      });
    }
    if (util != null && baseUtil != null && util + 0.05 < baseUtil) {
      insights.push({
        category: "reduced-human-workload",
        text: `${name} reduces resolution-team utilization from ${(baseUtil * 100).toFixed(0)}% to ${(util * 100).toFixed(0)}%.`,
      });
    }
  }
  const valid = (evidence.alternatives ?? []).filter((item) => item.status === "valid");
  if (valid.length >= 2) {
    const cycles = valid.map((item) => ({
      id: item.alternativeId,
      cycle: mean(item.systemMetrics?.averageCycleTime),
      wait: mean(item.stageMetrics?.resolution?.averageWaitingTime),
    }));
    const byCycle = [...cycles].sort((a, b) => (a.cycle ?? Infinity) - (b.cycle ?? Infinity));
    const byWait = [...cycles].sort((a, b) => (a.wait ?? Infinity) - (b.wait ?? Infinity));
    if (byCycle[0].id !== byWait[0].id && byCycle[0].cycle != null && byWait[0].wait != null) {
      insights.push({
        category: "objective-trade-off",
        text: `${LABELS[byCycle[0].id] ?? byCycle[0].id} has the lowest average cycle time in this experiment, while ${
          LABELS[byWait[0].id] ?? byWait[0].id
        } has the lowest resolution waiting. OpsTwin does not rank a universal winner.`,
      });
    }
  }
  return insights.slice(0, 8);
}
