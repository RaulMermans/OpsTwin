import assert from "node:assert/strict";
import test from "node:test";
import { contentFingerprint } from "./fingerprint.js";
import { generateSynthetic } from "./synthetic.js";
import { buildSnapshot } from "./snapshot.js";
import { goldenIssues } from "./synthetic.js";

test("golden snapshot has exact descriptive counts", () => {
  const snapshot = generateSynthetic("golden", 20261127, new Date("2026-10-15T00:00:00.000Z"));
  const byId = Object.fromEntries(snapshot.descriptiveEvidence.map((item) => [item.metricId, item]));
  assert.equal(byId.observed_case_count.value, 3);
  assert.equal(byId.origin_mix.value.synthetic, 3);
  assert.match(byId.observed_case_count.population, /synthetic=/);
  assert.equal(byId.resolution_count.value, 1);
  assert.equal(byId.reopen_count.value, 1);
  assert.equal(byId.arrivals_in_window.value, 3);
  assert.equal(byId.cycle_time_minutes.value.sampleSize, 1);
  assert.equal(byId.cycle_time_minutes.value.p50, 1440);
  assert.equal(byId.sla_cycle_count.value, 2);
  assert.equal(byId.sla_breach_count.value, 1);
  assert.equal(snapshot.schemaVersion, "os.1.0.0");
  assert.notEqual(snapshot.readiness, "valid");
  assert.ok(["potentially_suitable_for_calibration_assessment", "insufficient_for_calibration", "partial"].includes(snapshot.readiness));
});

test("content fingerprints ignore volatile import timestamps", () => {
  const first = generateSynthetic("golden", 1, new Date("2026-10-15T00:00:00.000Z"));
  const second = structuredClone(first);
  second.importTimestamp = "2099-01-01T00:00:00.000Z";
  second.importStartedAt = "2099-01-01T00:00:00.000Z";
  second.importCompletedAt = "2099-01-01T00:00:00.000Z";
  second.snapshotId = "other";
  assert.equal(contentFingerprint(second), first.contentFingerprint);
});

test("different case content changes the fingerprint", () => {
  const first = generateSynthetic("golden", 1, new Date("2026-10-15T00:00:00.000Z"));
  const second = generateSynthetic("stress", 1, new Date("2026-10-15T00:00:00.000Z"));
  assert.notEqual(first.contentFingerprint, second.contentFingerprint);
});

test("input ordering does not change normalized identity", () => {
  const window = { start: "2026-09-15T00:00:00.000Z", end: "2026-10-15T00:00:00.000Z", convention: "closed-start-open-end-utc", windowDays: 30 };
  const config = {
    windowDays: 30,
    recordLimit: 40,
    pageLimit: 8,
    cohortPolicy: "open-during-window",
    includeWorklogs: true,
    includeSla: true,
  };
  const extraction = {
    complete: true,
    truncatedReason: null,
    pageCount: 1,
    retryCount: 0,
    inconsistentSource: false,
    authorized: true,
    worklogCapability: "retrieved",
    slaCapability: "retrieved",
    changelogCapability: "retrieved",
  };
  const a = buildSnapshot({
    issues: goldenIssues(),
    requestTypes: [{ requestTypeId: "rt-help", name: "Get IT help" }],
    sourceProject: { reference: "project:OPS", key: "OPS", name: "Lab", serviceDeskId: "1" },
    window,
    importConfiguration: config,
    extraction,
    importStartedAt: "2026-10-15T00:00:00.000Z",
    importCompletedAt: "2026-10-15T00:00:00.000Z",
    evidenceClass: "synthetic",
    transportAuthenticity: "offline_fixture",
  });
  const b = buildSnapshot({
    issues: [...goldenIssues()].reverse(),
    requestTypes: [{ requestTypeId: "rt-help", name: "Get IT help" }],
    sourceProject: { reference: "project:OPS", key: "OPS", name: "Lab", serviceDeskId: "1" },
    window,
    importConfiguration: config,
    extraction,
    importStartedAt: "2026-10-15T00:00:00.000Z",
    importCompletedAt: "2026-10-15T00:00:00.000Z",
    evidenceClass: "synthetic",
    transportAuthenticity: "offline_fixture",
  });
  assert.equal(a.contentFingerprint, b.contentFingerprint);
});

test("valid empty extraction is empty, not a permission failure", () => {
  const snapshot = buildSnapshot({
    issues: [],
    requestTypes: [],
    sourceProject: { reference: "project:OPS", key: "OPS", name: "Lab", serviceDeskId: "1" },
    window: { start: "2026-09-15T00:00:00.000Z", end: "2026-10-15T00:00:00.000Z", convention: "closed-start-open-end-utc", windowDays: 30 },
    importConfiguration: {
      windowDays: 30,
      recordLimit: 40,
      pageLimit: 8,
      cohortPolicy: "open-during-window",
      includeWorklogs: true,
      includeSla: true,
    },
    extraction: {
      complete: true,
      truncatedReason: null,
      pageCount: 1,
      retryCount: 0,
      inconsistentSource: false,
      authorized: true,
      worklogCapability: "retrieved",
      slaCapability: "retrieved",
      changelogCapability: "retrieved",
    },
    importStartedAt: "2026-10-15T00:00:00.000Z",
    importCompletedAt: "2026-10-15T00:00:00.000Z",
    evidenceClass: "observed",
    transportAuthenticity: "live_api",
  });
  assert.equal(snapshot.completenessStatus, "empty");
  assert.equal(snapshot.readiness, "insufficient_for_calibration");
});

test("truncated extraction cannot be complete", () => {
  const snapshot = buildSnapshot({
    issues: goldenIssues(),
    requestTypes: [],
    sourceProject: { reference: "project:OPS", key: "OPS", name: "Lab", serviceDeskId: null },
    window: { start: "2026-09-15T00:00:00.000Z", end: "2026-10-15T00:00:00.000Z", convention: "closed-start-open-end-utc", windowDays: 30 },
    importConfiguration: {
      windowDays: 30,
      recordLimit: 40,
      pageLimit: 8,
      cohortPolicy: "open-during-window",
      includeWorklogs: true,
      includeSla: true,
    },
    extraction: {
      complete: false,
      truncatedReason: "page_budget",
      pageCount: 8,
      retryCount: 0,
      inconsistentSource: false,
      authorized: true,
      worklogCapability: "not_requested",
      slaCapability: "not_requested",
      changelogCapability: "partial",
    },
    importStartedAt: "2026-10-15T00:00:00.000Z",
    importCompletedAt: "2026-10-15T00:00:00.000Z",
    evidenceClass: "synthetic",
    transportAuthenticity: "offline_fixture",
  });
  assert.equal(snapshot.completenessStatus, "partial");
  assert.equal(snapshot.readiness, "partial");
});
