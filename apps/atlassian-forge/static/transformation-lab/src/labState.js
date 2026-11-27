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
