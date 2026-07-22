export type IntervalEvidence = { lower: number; upper: number } | null;
export type IntervalInterpretation = "favorable" | "inconclusive" | "unfavorable" | "unavailable";

/**
 * Interprets an already-returned confidence interval relative to no change.
 * It does not calculate an interval, rank scenarios, or create a probability.
 */
export function interpretReturnedInterval(interval: IntervalEvidence, direction: string): IntervalInterpretation {
  if (!interval || !Number.isFinite(interval.lower) || !Number.isFinite(interval.upper)) return "unavailable";
  const directedLower = direction === "minimize" ? -interval.upper : interval.lower;
  const directedUpper = direction === "minimize" ? -interval.lower : interval.upper;
  if (directedLower > 0) return "favorable";
  if (directedUpper < 0) return "unfavorable";
  return "inconclusive";
}

export function intervalInterpretationCopy(kind: IntervalInterpretation): string {
  if (kind === "favorable") return "The reported plausible range remained on the improvement side of no change.";
  if (kind === "inconclusive") return "The plausible range includes no improvement or a worse result. The evidence is inconclusive.";
  if (kind === "unfavorable") return "The reported plausible range indicates worse performance for this result.";
  return "A plausible range was not available for this result.";
}
