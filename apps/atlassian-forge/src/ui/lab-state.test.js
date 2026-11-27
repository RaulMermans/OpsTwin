import assert from "node:assert/strict";
import test from "node:test";
import { afterConfigChange, afterFailedImport, comparisonPayload, defaultConfig } from "../../static/transformation-lab/src/labState.js";

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

test("payloads stay on the synthetic catalog and omit project identity", () => {
  const capacity = comparisonPayload({ ...defaultConfig(), extraCapacity: 2 });
  assert.equal(capacity.intervention, "add-capacity");
  assert.equal(capacity.extraCapacity, 2);
  assert.equal("projectKey" in capacity, false);
  const triage = comparisonPayload({ ...defaultConfig(), intervention: "faster-triage", triageReductionPercent: 40 });
  assert.equal(triage.triageReductionPercent, 40);
});
