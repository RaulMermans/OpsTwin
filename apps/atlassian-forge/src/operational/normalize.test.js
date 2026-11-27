import assert from "node:assert/strict";
import test from "node:test";
import { dedupeEvents, eventsFromIssue, normalizeCase, reconstructLifecycle, statusRecord } from "./normalize.js";
import { durationMinutes, parseTimestamp } from "./time.js";
import { goldenIssues } from "./synthetic.js";
import { generateSynthetic } from "./synthetic.js";

const meta = {
  sourceSystem: "jira-jsm",
  projectReference: "project:OPS",
  evidenceClass: "synthetic",
  transportAuthenticity: "offline_fixture",
  observationWindowLabel: "w",
};

const window = { start: "2026-09-15T00:00:00.000Z", end: "2026-10-15T00:00:00.000Z", convention: "closed-start-open-end-utc" };

test("source timestamps convert to UTC including DST offsets", () => {
  const parsed = parseTimestamp("2026-03-29T02:30:00+01:00");
  assert.equal(parsed.ok, true);
  assert.equal(parsed.utcIso, "2026-03-29T01:30:00.000Z");
});

test("negative durations are rejected", () => {
  const result = durationMinutes("2026-10-02T00:00:00.000Z", "2026-10-01T00:00:00.000Z");
  assert.equal(result.ok, false);
  assert.equal(result.reason, "negative");
});

test("status mapping stays unresolved", () => {
  const status = statusRecord({ id: "3", name: "Done", statusCategory: { key: "done" } });
  assert.equal(status.operationalClass, "unresolved");
  assert.equal(status.mappingStatus, "unresolved");
});

test("golden case and reopen events are reconstructed without inventing an initial state", () => {
  const issues = goldenIssues();
  const complete = normalizeCase(issues[0], meta);
  const events = eventsFromIssue(issues[0], complete, meta);
  assert.equal(events[0].eventType, "case_created");
  assert.ok(events.some((item) => item.eventType === "resolved"));
  const open = normalizeCase(issues[1], meta);
  const openLifecycle = reconstructLifecycle(open, eventsFromIssue(issues[1], open, meta), window);
  assert.equal(openLifecycle.caseRecord.lifecycleCompleteness, "incomplete");
  const reopened = normalizeCase(issues[2], meta);
  const reopenedEvents = eventsFromIssue(issues[2], reopened, meta);
  assert.ok(reopenedEvents.some((item) => item.eventType === "reopened"));
  assert.ok(reopenedEvents.some((item) => item.eventType === "reassigned"));
});

test("duplicate events collapse and ordering is stable", () => {
  const issue = goldenIssues()[0];
  const caseRecord = normalizeCase(issue, meta);
  const events = eventsFromIssue(issue, caseRecord, meta);
  const duplicated = dedupeEvents([...events, events[1], events[1]]);
  assert.equal(duplicated.length, events.length);
  const reversed = dedupeEvents([...events].reverse());
  assert.deepEqual(
    reversed.map((item) => item.eventId),
    dedupeEvents(events).map((item) => item.eventId),
  );
});

test("out-of-order changelogs sort by occurredAt then type", () => {
  const issue = goldenIssues()[0];
  issue.changelog = [...issue.changelog].reverse();
  const caseRecord = normalizeCase(issue, meta);
  const events = dedupeEvents(eventsFromIssue(issue, caseRecord, meta));
  const times = events.map((item) => item.occurredAt);
  assert.deepEqual(times, [...times].sort());
});

test("missing request type stays null and issue type is not substituted", () => {
  const issue = { ...goldenIssues()[1], requestTypeId: null, issuetype: { id: "10001", name: "Task" } };
  const caseRecord = normalizeCase(issue, meta);
  assert.equal(caseRecord.requestTypeReference, null);
});

test("events before creation do not invent a start interval of known residence", () => {
  const issue = {
    key: "OPS-X",
    created: "2026-10-01T00:00:00.000Z",
    changelog: [{ id: "1", field: "status", created: "2026-09-01T00:00:00.000Z", from: "1", to: "2" }],
  };
  const caseRecord = normalizeCase(issue, meta);
  const lifecycle = reconstructLifecycle(caseRecord, eventsFromIssue(issue, caseRecord, meta), window);
  assert.ok(lifecycle.intervals.some((item) => item.intervalType === "unknown" || item.complete === false));
});

test("synthetic snapshots keep synthetic provenance", () => {
  const snapshot = generateSynthetic("golden");
  assert.equal(snapshot.provenance.evidenceClass, "synthetic");
  assert.ok(snapshot.cases.every((item) => item.provenance.evidenceClass === "synthetic"));
});
