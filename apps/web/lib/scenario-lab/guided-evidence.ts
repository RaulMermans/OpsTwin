export type GuidedEvidenceView = "summary" | "flow" | "risk" | "resources" | "sensitivity" | "economics" | "playback" | "technical";

export const guidedEvidenceViews: { id: GuidedEvidenceView; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "flow", label: "Flow" },
  { id: "risk", label: "Risk" },
  { id: "resources", label: "Resources" },
  { id: "sensitivity", label: "Sensitivity" },
  { id: "economics", label: "Economics" },
  { id: "playback", label: "Playback" },
  { id: "technical", label: "Technical" },
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
