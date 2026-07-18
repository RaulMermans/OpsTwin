import type { ScenarioDraft, ScenarioType } from "../scenarios/builders";

export const scenarioLabels: Record<ScenarioType, string> = {
  demand: "Demand increase",
  level1Staffing: "Level 1 staffing",
  level2Staffing: "Level 2 staffing",
  triageProcess: "Triage processing",
  quality: "Quality and rework",
};

export const scenarioInputLabels: Record<ScenarioType, string> = {
  demand: "Demand increase (%)",
  level1Staffing: "Level 1 agents added",
  level2Staffing: "Level 2 agents added",
  triageProcess: "Triage time reduction (%)",
  quality: "Rework reduction (%)",
};

export const scenarioSummary = (scenario: ScenarioDraft) =>
  `${scenarioInputLabels[scenario.type]}: ${scenario.value}${scenario.type === "level1Staffing" || scenario.type === "level2Staffing" ? "" : "%"}`;
