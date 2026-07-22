import { describe, expect, it } from "vitest";

import { intervalInterpretationCopy, interpretReturnedInterval } from "../lib/scenario-lab/guided-result-copy";
import { formatMetricDelta, formatPercentagePointChange, guidedMetricLabel } from "../lib/scenario-lab/metrics";

describe("Guided result wording helpers", () => {
  it("interprets returned ranges using the existing objective direction", () => {
    expect(interpretReturnedInterval({ lower: -4, upper: -1 }, "minimize")).toBe("favorable");
    expect(interpretReturnedInterval({ lower: -1, upper: 2 }, "minimize")).toBe("inconclusive");
    expect(interpretReturnedInterval({ lower: 1, upper: 4 }, "minimize")).toBe("unfavorable");
    expect(interpretReturnedInterval({ lower: 0.01, upper: 0.04 }, "maximize")).toBe("favorable");
    expect(interpretReturnedInterval(null, "maximize")).toBe("unavailable");
    expect(intervalInterpretationCopy("inconclusive")).toMatch(/includes no improvement or a worse result/i);
  });

  it("formats proportion deltas as percentage points and preserves target wording", () => {
    expect(formatPercentagePointChange(0.023)).toBe("+2.3 percentage points");
    expect(formatPercentagePointChange(-0.023)).toBe("-2.3 percentage points");
    expect(formatPercentagePointChange(0)).toBe("+0.0 percentage points");
    expect(formatPercentagePointChange(0.0004)).toBe("+0.0 percentage points");
    expect(formatMetricDelta("slaAttainment", 0.023)).toBe("+2.3 percentage points");
    expect(formatMetricDelta("slaAttainment", -0.023)).not.toMatch(/%/);
    expect(formatMetricDelta("averageCycleTime", -2)).toBe("-2.00 min");
    expect(guidedMetricLabel("slaAttainment", 60)).toBe("Tickets resolved within 60 minutes");
    expect(guidedMetricLabel("slaAttainment", 90)).toBe("Tickets resolved within 90 minutes");
  });
});
