export type EconomicDraft = {
  currency: string; level1CapacityRate: string; level2CapacityRate: string;
  stageVisitRate: string; queueHoldingRate: string; slaViolationRate: string;
  terminalFailureRate: string; reworkRate: string; fixedPeriodCost: string;
};

export const DEFAULT_ECONOMIC_DRAFT: EconomicDraft = {
  currency: "EUR", level1CapacityRate: "1", level2CapacityRate: "1", stageVisitRate: "",
  queueHoldingRate: "", slaViolationRate: "", terminalFailureRate: "", reworkRate: "", fixedPeriodCost: "",
};
const configured = (value: string) => value.trim() !== "";
const numeric = (value: string) => Number(value);

export function validateEconomicDraft(draft: EconomicDraft): string | null {
  if (!/^[A-Z]{3}$/.test(draft.currency)) return "Currency must use three uppercase letters.";
  const values = Object.entries(draft).filter(([key]) => key !== "currency").map(([, value]) => value);
  if (!values.some(configured)) return "Configure at least one cost category.";
  if (values.some((value) => configured(value) && (!Number.isFinite(numeric(value)) || numeric(value) < 0))) return "Configured costs must be finite and at least zero.";
  return null;
}

export function buildEconomicAssumptions(draft: EconomicDraft) {
  const resourceProvisioning = [["level-1-agents", draft.level1CapacityRate], ["level-2-agents", draft.level2CapacityRate]]
    .filter(([, value]) => configured(value)).map(([resourcePoolId, value]) => ({ resourcePoolId, costPerCapacityTimeUnit: numeric(value) }));
  return {
    schemaVersion: "0.7.0", currency: draft.currency, modelTimeUnit: "minutes",
    ...(resourceProvisioning.length ? { resourceProvisioning } : {}),
    ...(configured(draft.stageVisitRate) ? { stageVisit: [{ stageId: "triage", costPerVisit: numeric(draft.stageVisitRate) }] } : {}),
    ...(configured(draft.queueHoldingRate) ? { queueHolding: [{ costPerItemTimeUnit: numeric(draft.queueHoldingRate) }] } : {}),
    ...(configured(draft.slaViolationRate) ? { costPerSlaViolation: numeric(draft.slaViolationRate) } : {}),
    ...(configured(draft.terminalFailureRate) ? { costPerTerminalFailure: numeric(draft.terminalFailureRate) } : {}),
    ...(configured(draft.reworkRate) ? { rework: [{ costPerRework: numeric(draft.reworkRate) }] } : {}),
    ...(configured(draft.fixedPeriodCost) ? { fixedCostPerAnalysisPeriod: numeric(draft.fixedPeriodCost) } : {}),
  };
}

export function interventionFor(scenarioId: string, oneTimeCost: string, amortizationPeriods: string) {
  if (!configured(oneTimeCost)) return null;
  return { scenarioId, oneTimeCost: numeric(oneTimeCost), ...(configured(amortizationPeriods) ? { amortizationPeriods: numeric(amortizationPeriods) } : {}) };
}
