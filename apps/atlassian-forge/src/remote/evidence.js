const FINITE = (value) => typeof value === "number" && Number.isFinite(value);

function packedOk(metric, allowNull = true) {
  if (metric == null) return allowNull;
  if (typeof metric !== "object") return false;
  if (!FINITE(metric.mean)) return false;
  if (metric.lower != null && !FINITE(metric.lower)) return false;
  if (metric.upper != null && !FINITE(metric.upper)) return false;
  if (metric.lower != null && metric.upper != null && metric.lower > metric.upper) return false;
  if (typeof metric.unit !== "string" || metric.unit.length < 1) return false;
  return true;
}

function probabilityOk(value) {
  return value == null || (FINITE(value) && value >= 0 && value <= 1);
}

export function validateTransformEvidence(body, expected) {
  if (!body || typeof body !== "object") {
    return { ok: false, message: "The remote returned an empty experiment response." };
  }
  if (body.synthetic !== true) {
    return { ok: false, message: "The experiment response was not marked synthetic." };
  }
  if (body.identitiesAgree !== true) {
    return { ok: false, message: "The executed model did not match the calibrated identity." };
  }
  if (expected?.requestId && body.requestId && body.requestId !== expected.requestId) {
    return { ok: false, message: "The experiment response did not match the current request." };
  }
  if (expected?.experimentId && body.experimentId && body.experimentId !== expected.experimentId) {
    return { ok: false, message: "The experiment response did not match the current experiment." };
  }
  if (body.contractVersion === "cg5.v1") {
    if (!["complete", "partial", "failed"].includes(body.experimentStatus)) {
      return { ok: false, message: "The experiment status was missing." };
    }
    if (!Array.isArray(body.alternatives) || body.alternatives.length < 1) {
      return { ok: false, message: "The experiment did not include alternatives." };
    }
    if (body.experimentStatus === "complete") {
      if (body.alternatives.some((item) => item.status !== "valid")) {
        return { ok: false, message: "A complete experiment cannot include failed alternatives." };
      }
      if (body.integrityStatus !== "passed") {
        return { ok: false, message: "A complete experiment requires passed integrity." };
      }
    }
    if (typeof body.experimentIdentity !== "string" || body.experimentIdentity.length < 16) {
      return { ok: false, message: "Experiment identity was missing." };
    }
    if (expected?.alternativeIds) {
      const ids = body.alternatives.map((item) => item.alternativeId);
      if (ids.join("|") !== expected.alternativeIds.join("|")) {
        return { ok: false, message: "The experiment alternatives did not match the current request." };
      }
    }
    for (const alternative of body.alternatives) {
      if (!alternative?.alternativeId || !alternative.status) {
        return { ok: false, message: "An alternative was missing identity or status." };
      }
      if (alternative.status === "valid") {
        if (!packedOk(alternative.systemMetrics?.averageCycleTime, false)) {
          return { ok: false, message: "A valid alternative was missing cycle-time evidence." };
        }
        if (!probabilityOk(alternative.probabilityOfImprovement)) {
          return { ok: false, message: "Improvement frequency was outside [0, 1]." };
        }
        if (alternative.validPairedRunCount != null && alternative.validPairedRunCount < 1) {
          return { ok: false, message: "A valid alternative reported no paired replications." };
        }
      }
    }
    return { ok: true };
  }
  if (body.contractVersion && body.contractVersion !== "cg4.v1") {
    return { ok: false, message: "Unsupported experiment contract version." };
  }
  if (!FINITE(body.baselineCycleTime?.mean) || !FINITE(body.scenarioCycleTime?.mean)) {
    return { ok: false, message: "Cycle-time evidence was missing or invalid." };
  }
  if (!probabilityOk(body.probabilityOfImprovement)) {
    return { ok: false, message: "Improvement frequency was outside [0, 1]." };
  }
  return { ok: true };
}

export function validateEconomicEvidence(body, expected) {
  if (!body || typeof body !== "object") {
    return { ok: false, message: "The remote returned an empty economic response." };
  }
  if (body.contractVersion !== "cg6.v1" || body.synthetic !== true) {
    return { ok: false, message: "The economic response contract was invalid." };
  }
  if (body.integrityStatus !== "passed") {
    return { ok: false, message: "Economic evaluation integrity did not pass." };
  }
  if (expected?.experimentIdentity && body.operationalExperimentIdentity !== expected.experimentIdentity) {
    return { ok: false, message: "Economic results did not match the current operational experiment." };
  }
  if (!Array.isArray(body.strategies) || body.strategies.length < 1) {
    return { ok: false, message: "Economic evaluation did not include strategies." };
  }
  for (const strategy of body.strategies) {
    if (strategy.roi === 0 && strategy.incrementalInvestment === 0) {
      return { ok: false, message: "ROI cannot be zero when investment is unavailable." };
    }
  }
  return { ok: true };
}
