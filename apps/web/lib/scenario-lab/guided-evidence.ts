export type GuidedEvidenceView = "summary" | "flow" | "risk" | "resources" | "sensitivity" | "economics" | "playback" | "technical";

export const guidedEvidenceViews: { id: GuidedEvidenceView; label: string; purpose: string }[] = [
  { id: "summary", label: "Result", purpose: "What changed overall?" },
  { id: "flow", label: "Process", purpose: "Where does the change occur?" },
  { id: "risk", label: "Uncertainty", purpose: "How consistent was the result?" },
  { id: "resources", label: "Team workload", purpose: "Which teams became constrained?" },
  { id: "sensitivity", label: "Test assumptions", purpose: "Does the result change with different inputs?" },
  { id: "economics", label: "Costs", purpose: "What happens after adding supplied costs?" },
  { id: "playback", label: "Example run", purpose: "What happened during one simulated day?" },
  { id: "technical", label: "Technical details", purpose: "How was the experiment executed and checked?" },
];

export const guidedEvidenceTargets: Record<string, GuidedEvidenceView> = {
  "flow-evidence": "flow",
  "risk-evidence": "risk",
  "resources-evidence": "resources",
  "sensitivity-evidence": "sensitivity",
  "economics-evidence": "economics",
  "playback-evidence": "playback",
  "technical-evidence": "technical",
};
