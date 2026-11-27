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
    kind: "capacity",
    extraTriageCapacity: 1,
    extraResolutionCapacity: 1,
    stageId: "triage",
    coverage: 0.5,
    processingReduction: 0.4,
    reviewOverheadMinutes: 0.25,
    autoCompleteFraction: 0.25,
    itemCount: 40,
    runCount: 5,
  };
}

export function transformPayload(calibration, transform) {
  let intervention;
  if (transform.kind === "capacity") {
    intervention = {
      kind: "capacity",
      extraTriageCapacity: transform.extraTriageCapacity,
      extraResolutionCapacity: transform.extraResolutionCapacity,
    };
  } else if (transform.kind === "ai_assisted") {
    intervention = {
      kind: "ai_assisted",
      stageId: transform.stageId,
      coverage: transform.coverage,
      processingReduction: transform.processingReduction,
      reviewOverheadMinutes: transform.reviewOverheadMinutes,
    };
  } else {
    intervention = {
      kind: "hybrid",
      autoCompleteFraction: transform.autoCompleteFraction,
      coverage: 0,
      processingReduction: 0,
      reviewOverheadMinutes: 0,
    };
  }
  return {
    fixtureId: calibration.fixtureId,
    approveLabAssumptions: calibration.approveLabAssumptions,
    randomSeed: 20260327,
    intervention,
    execution: {
      itemCount: transform.itemCount,
      runCount: transform.runCount,
      baseSeed: 20261127,
    },
  };
}
