import canonicalBaseline from "./support-operations-baseline.json";

export type BaselineForm = {
  arrivalInterval: number; triageDuration: number; level1Capacity: number; level2Capacity: number;
  qualityDuration: number; escalationProbability: number; reworkProbability: number; slaTarget: number;
};

export const DEFAULT_FORM: Readonly<BaselineForm> = Object.freeze({ arrivalInterval: 1.5, triageDuration: 2, level1Capacity: 4, level2Capacity: 2, qualityDuration: 2, escalationProbability: 20, reworkProbability: 10, slaTarget: 60 });
export type BaselineModel = typeof canonicalBaseline;

export function buildBaseline(form: BaselineForm): BaselineModel {
  const model = structuredClone(canonicalBaseline);
  model.sources[0].arrival.meanInterarrivalTime = form.arrivalInterval;
  model.resourcePools.find((pool) => pool.id === "level-1-agents")!.capacity = form.level1Capacity;
  model.resourcePools.find((pool) => pool.id === "level-2-agents")!.capacity = form.level2Capacity;
  model.stages.find((stage) => stage.id === "triage")!.processingTime = { type: "exponential", mean: form.triageDuration };
  const quality = model.stages.find((stage) => stage.id === "quality-check")!;
  quality.processingTime = { type: "fixed", value: form.qualityDuration };
  quality.failure!.probability = form.reworkProbability / 100;
  const route = model.routes.find((item) => item.id === "triage-routing")!;
  route.options[0].probability = 1 - form.escalationProbability / 100;
  route.options[1].probability = form.escalationProbability / 100;
  model.slaRules[0].targetDuration = form.slaTarget;
  return model;
}
