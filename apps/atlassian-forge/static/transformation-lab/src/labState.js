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
  { id: "decision", label: "Investment Decision" },
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
    JSON.stringify(alternatives),
  ].join(":");
}

export function defaultManualSpec() {
  return {
    expectedVolume: 400,
    observationDays: 30,
    operatingHoursPerDay: 8,
    triageCapacity: 2,
    resolutionCapacity: 3,
    triageMeanMinutes: 8,
    resolutionMeanMinutes: 20,
    triageToResolutionProbability: 0.7,
    slaMinutes: 240,
  };
}

export const CSV_TEMPLATE = `case_id,activity,timestamp,work_duration_minutes,processing_stage,outcome
CASE-1,created,2026-01-05T08:00:00.000Z,,,
CASE-1,triage_started,2026-01-05T08:04:00.000Z,5,triage,
CASE-1,triage_completed,2026-01-05T08:10:00.000Z,,,
CASE-1,resolution_started,2026-01-05T08:12:00.000Z,18,resolution,
CASE-1,resolved,2026-01-05T08:35:00.000Z,,,completed
CASE-2,created,2026-01-05T09:00:00.000Z,,,
CASE-2,triage_started,2026-01-05T09:06:00.000Z,7,triage,
CASE-2,resolved,2026-01-05T09:20:00.000Z,,,completed
`;

export function defaultAssumptions(inventory) {
  return {
    schemaVersion: "cg7.v1",
    currency: "EUR",
    origin: "synthetic_demonstration",
    evaluationBasis: "fixed_workload",
    expectedDemandPerMonth: 400,
    evaluationMonths: 12,
    monthlyStaffCostPerFte: 6500,
    paidHoursPerMonth: 160,
    baselineTriageFte: inventory?.triageCapacity ?? 1,
    baselineResolutionFte: inventory?.resolutionCapacity ?? 1,
    aiSubscriptionMonthly: 800,
    aiCostPerAutomatedCase: 0,
    implementationCost: 12000,
    realizationMechanism: "none",
    realizationRate: 0,
    valueReleasedCapacity: false,
  };
}

export function defaultConstraints() {
  return {
    maximumImplementationCost: "",
    maximumRecurringMonthly: "",
    maximumCycleTime: "",
    minimumCompletions: "",
    maximumPaybackMonths: "",
  };
}

export function economicsPayload(calibration, transform, experiment, assumptions, constraints, requestId, explore) {
  const alternatives = selectedAlternatives(transform, calibration);
  const payload = {
    contractVersion: "cg7.v1",
    fixtureId: calibration.fixtureId,
    alternatives,
    execution: {
      itemCount: transform.itemCount,
      runCount: transform.runCount,
      baseSeed: 20261127,
    },
    experimentIdentity: experiment.evidence.experimentIdentity,
    evidenceToken: experiment.evidence.evidenceToken,
    assumptions,
    constraints: Object.fromEntries(
      Object.entries(constraints)
        .filter(([, value]) => value !== "" && value != null)
        .map(([key, value]) => [key, Number(value)]),
    ),
    requestId,
  };
  if (explore) payload.explore = explore;
  return payload;
}

export function afterFinancialChange(previous) {
  if (!previous?.evidence) return previous;
  return {
    ...previous,
    status: "stale",
    message: "Economic results are stale because financial assumptions changed. Operational evidence was kept.",
  };
}

export function decisionBriefText(brief) {
  if (!brief) return "";
  return [
    `Baseline: ${brief.baseline}`,
    `Strategies: ${(brief.strategies ?? []).join(", ")}`,
    "",
    "Operational findings",
    ...(brief.operationalFindings ?? []),
    "",
    "Economic findings",
    ...(brief.economicFindings ?? []),
    "",
    "Key assumptions",
    ...(brief.keyAssumptions ?? []),
    "",
    brief.breakEven ? `Break-even: ${brief.breakEven}` : null,
    "",
    "Material risks",
    ...(brief.materialRisks ?? []),
    "",
    `Next action: ${brief.suggestedNextAction}`,
  ]
    .filter((line) => line != null)
    .join("\n");
}

export function transformPayload(calibration, transform, requestId) {
  const alternatives = selectedAlternatives(transform, calibration);
  return {
    contractVersion: "cg5.v1",
    fixtureId: calibration.fixtureId,
    sourceMode: calibration.sourceMode || "synthetic",
    baselineToken: calibration.evidence?.baselineToken,
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

export function originForSource(mode) {
  if (mode === "manual") return "user_defined_exploratory";
  if (mode === "jira") return "source_linked_exploratory";
  if (mode === "csv") return "csv_exploratory";
  return "synthetic_demonstration";
}

export function sourceLinkedCalibrationPayload(preview, staffing, mappingReviewed) {
  const mapping = preview?.suggestedMapping ?? { mappingVersion: "status-role.1", statuses: [], reviewed: false };
  return {
    snapshotReference: preview?.snapshotFingerprint ?? "jira",
    snapshotFingerprint: preview?.snapshotFingerprint,
    operationalMapping: {
      mappingVersion: "status-role.1",
      reviewed: mappingReviewed === true,
      requestTypeClasses: mapping.requestTypeClasses ?? {},
      statuses: (mapping.statuses ?? []).map((item) => ({
        statusId: item.statusId,
        role: item.role,
        stageId: item.stageId ?? null,
        reviewed: mappingReviewed === true,
      })),
    },
    assumptionSet: [
      ["triage.processing_time.mean", staffing.triageMeanMinutes, "minutes"],
      ["resolution.processing_time.mean", staffing.resolutionMeanMinutes, "minutes"],
      ["resource.triage-team.capacity", staffing.triageCapacity, "servers"],
      ["resource.resolution-team.capacity", staffing.resolutionCapacity, "servers"],
    ].map(([id, value, unit]) => ({
      assumptionId: id,
      affectedParameter: id,
      proposedValue: value,
      unit,
      rationale: "Explicit analyst assumption. Status residence is not used as processing time.",
      source: "analyst",
      approvalStatus: "approved",
      revision: 1,
      limitations: ["Not inferred from assignees or dwell time."],
      evidenceAvailable: "none identifiable",
      operationalConsequence: "Binds the executed exploratory model.",
    })),
    estimationConfiguration: {
      treatWorklogsAsProcessing: false,
      allowAssumptionBasedModel: true,
    },
    randomSeed: 20260327,
  };
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
