import assert from "node:assert/strict";
import test from "node:test";
import { afterCalibrationChange, afterConfigChange, afterFailedImport, calibrationPayload, comparisonPayload, defaultConfig, defaultTransform, hybridSupported, selectedAlternatives, transformPayload } from "../../static/transformation-lab/src/labState.js";

test("configuration changes invalidate displayed evidence", () => {
  const stale = afterConfigChange({
    evidence: { baseSeed: 1 },
    status: "completed",
    message: null,
  });
  assert.equal(stale.evidence, null);
  assert.equal(stale.status, "ready");
});

test("failed imports do not keep the previous snapshot as current", () => {
  const result = afterFailedImport({ snapshotId: "old" });
  assert.equal(result.snapshot, null);
  assert.equal(result.stale, true);
});

test("calibration payloads are fixture identifiers only", () => {
  const payload = calibrationPayload("cg3-golden-analytical", true);
  assert.equal(payload.fixtureId, "cg3-golden-analytical");
  assert.equal(payload.approveLabAssumptions, true);
  assert.equal(calibrationPayload("cg3-golden-analytical").approveLabAssumptions, false);
  assert.equal("snapshot" in payload, false);
  assert.equal("projectKey" in payload, false);
  const stale = afterCalibrationChange({ evidence: { readinessStatus: "validated_for_defined_scope" }, status: "completed" });
  assert.equal(stale.evidence, null);
});

test("payloads stay on the synthetic catalog and omit project identity", () => {
  const capacity = comparisonPayload({ ...defaultConfig(), extraCapacity: 2 });
  assert.equal(capacity.intervention, "add-capacity");
  assert.equal(capacity.extraCapacity, 2);
  assert.equal("projectKey" in capacity, false);
  const triage = comparisonPayload({ ...defaultConfig(), intervention: "faster-triage", triageReductionPercent: 40 });
  assert.equal(triage.triageReductionPercent, 40);
});

test("transformation payloads stay on fixture identifiers and experiment volume", () => {
  const payload = transformPayload(
    { fixtureId: "cg5-hybrid-support", approveLabAssumptions: true, evidence: { hybridCompatible: true, constructedModel: {} } },
    defaultTransform(),
    "req-1",
  );
  assert.equal(payload.contractVersion, "cg5.v1");
  assert.equal(payload.fixtureId, "cg5-hybrid-support");
  assert.equal(payload.execution.itemCount, 20);
  assert.notEqual(payload.execution.itemCount, 1);
  assert.equal(payload.alternatives.length, 3);
  assert.equal(payload.requestId, "req-1");
  assert.equal("snapshot" in payload, false);
  assert.equal("baselineModel" in payload, false);
  assert.equal("projectKey" in payload, false);
});

test("hybrid is omitted when the baseline has no completion route", () => {
  const calibration = { fixtureId: "cg3-golden-analytical", evidence: { hybridCompatible: false } };
  assert.equal(hybridSupported(calibration), false);
  const alternatives = selectedAlternatives(defaultTransform(), calibration);
  assert.equal(alternatives.some((item) => item.alternativeId === "hybrid"), false);
});
