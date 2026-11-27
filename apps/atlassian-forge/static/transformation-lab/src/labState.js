export const INTERVENTIONS = {
  "add-capacity": {
    id: "add-capacity",
    label: "Increase human resource capacity",
    parameter: "extraCapacity",
    options: [1, 2],
  },
  "faster-triage": {
    id: "faster-triage",
    label: "Reduce triage processing duration",
    parameter: "triageReductionPercent",
    options: [10, 25, 40],
  },
};

export const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "data", label: "Operational Data" },
  { id: "baseline", label: "Baseline Model" },
  { id: "lab", label: "Transformation Lab" },
  { id: "results", label: "Results & Evidence" },
];

export const COLORS = {
  baseline: "#44546F",
  "human-expansion": "#0C66E4",
  "ai-assisted": "#5E4DB2",
  hybrid: "#E56910",
};

export function defaultConfig() {
  return {
    intervention: "add-capacity",
    extraCapacity: 1,
    triageReductionPercent: 25,
    runCount: 5,
  };
}

export function comparisonPayload(config) {
  if (config.intervention === "add-capacity") {
    return {
      intervention: "add-capacity",
      extraCapacity: config.extraCapacity,
      runCount: config.runCount,
    };
  }
  return {
    intervention: "faster-triage",
    triageReductionPercent: config.triageReductionPercent,
    runCount: config.runCount,
  };
}

export function afterConfigChange(previous) {
  if (!previous.evidence) return previous;
  return { ...previous, evidence: null, status: "ready", message: "Previous results are stale because the configuration changed." };
}

export const WINDOW_PRESETS = [30, 60, 90];

export function defaultImportConfig() {
  return { windowDays: 30 };
}

export function afterFailedImport(previousSnapshot) {
  return { snapshot: null, previousSnapshot: previousSnapshot ?? null, stale: Boolean(previousSnapshot) };
}

export function metricById(snapshot, metricId) {
  return snapshot?.descriptiveEvidence?.find((item) => item.metricId === metricId) ?? null;
}

export function calibrationPayload(fixtureId, approveLabAssumptions = false) {
  return {
    fixtureId,
    approveLabAssumptions,
    randomSeed: 20260327,
  };
}

export function afterCalibrationChange(previous) {
  if (!previous?.evidence) return previous;
  return {
    ...previous,
    evidence: null,
    status: "ready",
    message: "Previous calibration results are stale because the configuration changed.",
  };
}

export function defaultTransform() {
  return {
    includeCapacity: true,
    includeAssisted: true,
    includeHybrid: true,
    extraTriageCapacity: 1,
    extraResolutionCapacity: 1,
    stageId: "triage",
    coverage: 0.5,
    processingReduction: 0.4,
    reviewOverheadMinutes: 0.25,
    autoCompleteFraction: 0.25,
    itemCount: 20,
    runCount: 5,
    sensitivityParameter: "coverage",
  };
}

export function hybridSupported(calibration) {
  if (calibration?.evidence?.hybridCompatible === true) return true;
  return calibration?.evidence?.baselineInventory?.hybridCompatible === true;
}

export function selectedAlternatives(transform, calibration) {
  const alternatives = [];
  if (transform.includeCapacity) {
    alternatives.push({
      alternativeId: "human-expansion",
      intervention: {
        kind: "capacity",
        extraTriageCapacity: transform.extraTriageCapacity,
        extraResolutionCapacity: transform.extraResolutionCapacity,
      },
    });
  }
  if (transform.includeAssisted) {
    alternatives.push({
      alternativeId: "ai-assisted",
      intervention: {
        kind: "ai_assisted",
        stageId: transform.stageId,
        coverage: transform.coverage,
        processingReduction: transform.processingReduction,
        reviewOverheadMinutes: transform.reviewOverheadMinutes,
      },
    });
  }
  if (transform.includeHybrid && hybridSupported(calibration)) {
    alternatives.push({
      alternativeId: "hybrid",
      intervention: {
        kind: "hybrid",
        autoCompleteFraction: transform.autoCompleteFraction,
        coverage: 0,
        processingReduction: 0,
        reviewOverheadMinutes: 0,
      },
    });
  }
  return alternatives;
}

export function experimentIdFor(calibration, transform, alternatives) {
  return [
    calibration.fixtureId,
    transform.itemCount,
    transform.runCount,
    alternatives.map((item) => item.alternativeId).join("+"),
  ].join(":");
}

export function transformPayload(calibration, transform, requestId) {
  const alternatives = selectedAlternatives(transform, calibration);
  return {
    contractVersion: "cg5.v1",
    fixtureId: calibration.fixtureId,
    approveLabAssumptions: calibration.approveLabAssumptions,
    randomSeed: 20260327,
    alternatives,
    execution: {
      itemCount: transform.itemCount,
      runCount: transform.runCount,
      baseSeed: 20261127,
    },
    experimentId: experimentIdFor(calibration, transform, alternatives),
    requestId,
  };
}

export function sensitivityPayload(calibration, transform, requestId) {
  const parameter = transform.sensitivityParameter;
  const values =
    parameter === "coverage"
      ? [0.25, 0.5, 0.75]
      : parameter === "processingReduction"
        ? [0.2, 0.4, 0.6]
        : parameter === "autoCompleteFraction"
          ? [0.1, 0.25, 0.4]
          : [1, 2, 3];
  const alternatives = values.map((value, index) => {
    const labels = ["low", "base", "high"];
    if (parameter === "extraResolutionCapacity") {
      return {
        alternativeId: `capacity-${labels[index]}`,
        intervention: { kind: "capacity", extraTriageCapacity: 0, extraResolutionCapacity: value },
      };
    }
    if (parameter === "autoCompleteFraction") {
      return {
        alternativeId: `hybrid-${labels[index]}`,
        intervention: {
          kind: "hybrid",
          autoCompleteFraction: value,
          coverage: 0,
          processingReduction: 0,
          reviewOverheadMinutes: 0,
        },
      };
    }
    return {
      alternativeId: `assisted-${labels[index]}`,
      intervention: {
        kind: "ai_assisted",
        stageId: transform.stageId,
        coverage: parameter === "coverage" ? value : transform.coverage,
        processingReduction: parameter === "processingReduction" ? value : transform.processingReduction,
        reviewOverheadMinutes: transform.reviewOverheadMinutes,
      },
    };
  });
  return {
    contractVersion: "cg5.v1",
    fixtureId: calibration.fixtureId,
    approveLabAssumptions: calibration.approveLabAssumptions,
    randomSeed: 20260327,
    alternatives,
    execution: {
      itemCount: transform.itemCount,
      runCount: transform.runCount,
      baseSeed: 20261127,
    },
    experimentId: `sensitivity:${parameter}:${experimentIdFor(calibration, transform, alternatives)}`,
    requestId,
  };
}

export function formatMetric(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return "unavailable";
  return Number(value).toFixed(digits);
}

export function formatInterval(metric) {
  if (!metric || metric.lower == null || metric.upper == null) return "unavailable";
  return `${formatMetric(metric.lower)} to ${formatMetric(metric.upper)}`;
}

export function baselineStatusLabel(evidence) {
  if (!evidence) return "Not constructed";
  if (!evidence.constructedModel) return "Insufficient evidence";
  if (evidence.readinessStatus === "validated_for_defined_scope") {
    return "Historical validation passed for a defined scope";
  }
  if (evidence.readinessStatus === "validation_failed") return "Historical validation failed";
  if (evidence.validationReport?.overallOutcome === "inconclusive") return "Historical validation inconclusive";
  if ((evidence.parameterEstimates ?? []).some((item) => item.origin === "approved_assumption")) {
    return "Exploratory model (assumptions required)";
  }
  return "Model constructed";
}
