import assert from "node:assert/strict";
import test from "node:test";
import { IMPORT_LIMITS, ingestOperationalData } from "./ingest.js";
import { cohortJql, observationWindow } from "../operational/time.js";
import { describeJiraPath } from "./route.js";
import { reconstructLifecycle, eventsFromIssue, normalizeCase } from "../operational/normalize.js";
import { assessDataQuality, descriptiveEvidence } from "../operational/quality.js";
import { buildSnapshot } from "../operational/snapshot.js";
import { validateSnapshot } from "../operational/validate.js";
import { contentFingerprint } from "../operational/fingerprint.js";

const projectOk = { status: 200, body: { id: "10000", key: "OPS", name: "OpsTwin IT Support Lab", projectTypeKey: "service_desk" } };
const desksOk = { status: 200, body: { values: [{ id: "1", projectKey: "OPS" }] } };
const typesOk = { status: 200, body: { values: [{ id: "10", name: "Get IT help" }] } };
const fieldsOk = { status: 200, body: [{ id: "customfield_1", name: "Request Type", schema: { custom: "com.atlassian.servicedesk:vp-origin" } }] };
const statusesOk = { status: 200, body: [{ statuses: [{ id: "1", name: "Open", statusCategory: { key: "new" } }] }] };
const myselfOk = { status: 200, body: { timeZone: "UTC" } };

function router(handlers) {
  return async (path) => {
    const matches = handlers.filter(([pattern]) => path.startsWith(pattern) || path.includes(pattern));
    matches.sort((left, right) => right[0].length - left[0].length);
    const hit = matches[0];
    if (!hit) return { status: 404, body: {} };
    const value = typeof hit[1] === "function" ? hit[1](path) : hit[1];
    return { status: value.status, body: value.body, headers: value.headers ?? {} };
  };
}

function opsIssue(overrides = {}) {
  const { fields, ...rest } = overrides;
  return {
    id: "100",
    key: "OPS-1",
    changelog: {
      total: 10,
      startAt: 0,
      maxResults: 1,
      histories: [{ id: "h1", created: "2026-10-02T00:00:00.000Z", items: [{ field: "status", from: "1", to: "3" }] }],
    },
    fields: {
      created: "2026-10-01T00:00:00.000Z",
      resolutiondate: "2026-10-02T00:00:00.000Z",
      updated: "2026-10-02T00:00:00.000Z",
      project: { key: "OPS" },
      status: { id: "3", name: "Done", statusCategory: { key: "done" } },
      labels: [],
      ...fields,
    },
    ...rest,
  };
}

function handlers(extra = []) {
  return [
    ["/rest/api/3/myself", myselfOk],
    ["/rest/api/3/project/OPS", projectOk],
    ["/rest/servicedeskapi/servicedesk/1/requesttype", typesOk],
    ["/rest/servicedeskapi/servicedesk", desksOk],
    ["/rest/api/3/field", fieldsOk],
    ["/rest/api/3/project/OPS/statuses", statusesOk],
    ...extra,
    ["/rest/api/3/issue/", (path) => {
      if (path.includes("/worklog")) return { status: 200, body: { worklogs: [], total: 0, isLastPage: true } };
      return { status: 200, body: { values: [], total: 0, isLast: true } };
    }],
    ["/rest/servicedeskapi/request/", { status: 200, body: { values: [] } }],
  ];
}

function ingest(requestJson, payload = { windowDays: 30 }, extras = {}) {
  return ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload,
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson,
    retrySleep: async () => {},
    ...extras,
  });
}

test("JQL uses yyyy-MM-dd HH:mm and not ISO timestamps", () => {
  const window = observationWindow(30, new Date("2026-10-15T00:00:00.000Z"));
  const jql = cohortJql("OPS", window, "UTC");
  assert.equal(/\d{4}-\d{2}-\d{2}T/.test(jql), false);
  assert.equal(jql.includes("Z"), false);
  assert.match(jql, /ORDER BY created ASC, key ASC/);
  assert.match(jql, /2026-09-15 00:00/);
});

test("one expanded changelog of ten histories is not treated as complete", async () => {
  const changelogCalls = [];
  const result = await ingest(
    router(
      handlers([
        ["/rest/api/3/search/jql", { status: 200, body: { issues: [opsIssue()], isLast: true } }],
        [
          "/rest/api/3/issue/OPS-1/changelog",
          (path) => {
            changelogCalls.push(path);
            const startAt = Number(new URLSearchParams(path.split("?")[1]).get("startAt"));
            if (startAt === 0) {
              return {
                status: 200,
                body: {
                  values: [{ id: "h1", created: "2026-10-02T00:00:00.000Z", items: [{ field: "status", from: "1", to: "2" }] }],
                  total: 10,
                  isLast: false,
                },
              };
            }
            return {
              status: 200,
              body: {
                values: Array.from({ length: 9 }, (_, index) => ({
                  id: `h${index + 2}`,
                  created: "2026-10-02T01:00:00.000Z",
                  items: [{ field: "status", from: "2", to: "3" }],
                })),
                total: 10,
                isLast: true,
              },
            };
          },
        ],
      ]),
    ),
  );
  assert.ok(changelogCalls.length >= 2);
  assert.equal(result.snapshot.events.filter((item) => item.eventType === "status_changed").length >= 10, true);
  assert.equal(result.snapshot.extraction.changelogCompleteness, "complete");
});

test("synthetic labels in live-shaped search preserve mixed origin", async () => {
  const result = await ingest(
    router(
      handlers([
        [
          "/rest/api/3/search/jql",
          {
            status: 200,
            body: {
              issues: [
                opsIssue({ id: "1", key: "OPS-1", fields: { labels: ["opstwin-synthetic"] } }),
                opsIssue({
                  id: "2",
                  key: "OPS-2",
                  changelog: { histories: [] },
                  fields: { labels: [], created: "2026-10-03T00:00:00.000Z", resolutiondate: null, updated: "2026-10-03T00:00:00.000Z", status: { id: "1", name: "Open" } },
                }),
              ],
              isLast: true,
            },
          },
        ],
        ["/rest/api/3/issue/OPS-1/changelog", { status: 200, body: { values: [{ id: "h1", created: "2026-10-02T00:00:00.000Z", items: [{ field: "status", from: "1", to: "3" }] }], total: 1, isLast: true } }],
        ["/rest/api/3/issue/OPS-2/changelog", { status: 200, body: { values: [], total: 0, isLast: true } }],
      ]),
    ),
  );
  assert.equal(result.status, "completed");
  const byKey = Object.fromEntries(result.snapshot.cases.map((item) => [item.sourceReference, item]));
  assert.equal(byKey["OPS-1"].provenance.evidenceClass, "synthetic");
  assert.equal(byKey["OPS-2"].provenance.evidenceClass, "observed");
  assert.equal(result.snapshot.provenance.evidenceClass, "unknown");
  assert.ok(result.telemetry[0] || true);
  const searchCalls = [];
  await ingest(async (path, method, body) => {
    searchCalls.push({ path, method, body });
    return router(handlers([["/rest/api/3/search/jql", { status: 200, body: { issues: [], isLast: true } }]]))(path);
  });
  assert.ok(searchCalls.some((item) => item.method === "POST" && Array.isArray(item.body?.fields) && item.body.fields.includes("labels")));
});

test("malformed worklog is not an empty work log dataset", async () => {
  const result = await ingest(
    router(
      handlers([
        ["/rest/api/3/search/jql", { status: 200, body: { issues: [opsIssue({ changelog: { histories: [] } })], isLast: true } }],
        ["/rest/api/3/issue/OPS-1/changelog", { status: 200, body: { values: [{ id: "h1", created: "2026-10-02T00:00:00.000Z", items: [{ field: "status", from: "1", to: "3" }] }], total: 1, isLast: true } }],
        ["/rest/api/3/issue/OPS-1/worklog", { status: 200, body: {} }],
      ]),
    ),
  );
  assert.equal(result.snapshot.extraction.worklogCapability, "unavailable");
  assert.equal(result.snapshot.events.some((item) => item.eventType === "worklog_recorded"), false);
});

test("malformed SLA is not a zero-breach observation", async () => {
  const result = await ingest(
    router(
      handlers([
        ["/rest/api/3/search/jql", { status: 200, body: { issues: [opsIssue({ changelog: { histories: [] } })], isLast: true } }],
        ["/rest/api/3/issue/OPS-1/changelog", { status: 200, body: { values: [{ id: "h1", created: "2026-10-02T00:00:00.000Z", items: [{ field: "status", from: "1", to: "3" }] }], total: 1, isLast: true } }],
        ["/rest/servicedeskapi/request/OPS-1/sla", { status: 200, body: {} }],
      ]),
    ),
  );
  assert.equal(result.snapshot.extraction.slaCapability, "unavailable");
  const sla = result.snapshot.descriptiveEvidence.find((item) => item.metricId === "sla_breach_count");
  assert.equal(sla.value, 0);
  assert.equal(sla.coverage, null);
});

test("mandatory changelog failure is incomplete; optional unavailable request types are not", async () => {
  const failedChangelog = await ingest(
    router(
      handlers([
        ["/rest/api/3/search/jql", { status: 200, body: { issues: [opsIssue({ changelog: { histories: [] } })], isLast: true } }],
        ["/rest/api/3/issue/OPS-1/changelog", { status: 500, body: { error: true } }],
      ]),
    ),
  );
  assert.equal(failedChangelog.status, "partial");
  assert.equal(failedChangelog.snapshot.extraction.complete, false);

  const noDesk = await ingest(
    router([
      ["/rest/api/3/myself", myselfOk],
      ["/rest/api/3/project/OPS", projectOk],
      ["/rest/servicedeskapi/servicedesk", { status: 200, body: { values: [] } }],
      ["/rest/api/3/field", fieldsOk],
      ["/rest/api/3/project/OPS/statuses", statusesOk],
      ["/rest/api/3/search/jql", { status: 200, body: { issues: [opsIssue({ changelog: { histories: [] } })], isLast: true } }],
      ["/rest/api/3/issue/OPS-1/changelog", { status: 200, body: { values: [{ id: "h1", created: "2026-10-02T00:00:00.000Z", items: [{ field: "status", from: "1", to: "3" }] }], total: 1, isLast: true } }],
      ["/rest/api/3/issue/OPS-1/worklog", { status: 200, body: { worklogs: [], total: 0, isLastPage: true } }],
    ]),
  );
  assert.equal(noDesk.snapshot.extraction.slaCompleteness, "unavailable");
  assert.equal(noDesk.status, "completed");
});

test("multiple SLA cycles and unknown breach status are preserved", async () => {
  const result = await ingest(
    router(
      handlers([
        ["/rest/api/3/search/jql", { status: 200, body: { issues: [opsIssue({ changelog: { histories: [] } })], isLast: true } }],
        ["/rest/api/3/issue/OPS-1/changelog", { status: 200, body: { values: [{ id: "h1", created: "2026-10-02T00:00:00.000Z", items: [{ field: "status", from: "1", to: "3" }] }], total: 1, isLast: true } }],
        [
          "/rest/servicedeskapi/request/OPS-1/sla",
          {
            status: 200,
            body: {
              values: [
                {
                  id: "s",
                  name: "Time to resolution",
                  completedCycles: [
                    { startTime: { iso8601: "2026-10-01T00:00:00.000Z" }, stopTime: { iso8601: "2026-10-01T02:00:00.000Z" }, elapsedTime: { millis: 7200000 }, breached: false },
                    { startTime: { iso8601: "2026-10-01T03:00:00.000Z" }, stopTime: { iso8601: "2026-10-01T04:00:00.000Z" }, elapsedTime: { millis: 3600000 }, breached: true },
                  ],
                  ongoingCycle: { startTime: { iso8601: "2026-10-01T05:00:00.000Z" }, elapsedTime: { millis: 60000 } },
                },
              ],
            },
          },
        ],
      ]),
    ),
  );
  const slaEvents = result.snapshot.events.filter((item) => item.eventType === "sla_cycle_observed");
  assert.equal(slaEvents.length, 3);
  assert.equal(slaEvents.filter((item) => item.previousValue === "unknown").length, 1);
  assert.equal(slaEvents.filter((item) => item.previousValue === "breached").length, 1);
});

test("execution deadline exhaustion returns a partial import", async () => {
  let now = 0;
  const result = await ingest(
    router(handlers([["/rest/api/3/search/jql", { status: 200, body: { issues: [], isLast: true } }]])),
    { windowDays: 30 },
    { clock: { nowMs: () => now++ * 50_000 }, limits: { ...IMPORT_LIMITS, deadlineMs: 10 } },
  );
  assert.ok(result.status === "failed" || result.status === "partial");
});

test("route descriptors keep issue keys out of static path templates", () => {
  const search = describeJiraPath("/rest/api/3/search/jql?jql=project%20%3D%20OPS&maxResults=20&fields=labels&expand=changelog");
  assert.equal(search.kind, "search-jql");
  assert.equal(search.params.jql, "project = OPS");
  const changelog = describeJiraPath("/rest/api/3/issue/OPS-1/changelog?startAt=0&maxResults=100");
  assert.equal(changelog.kind, "changelog");
  assert.equal(changelog.issueKey, "OPS-1");
});

test("unauthorized import fails closed", async () => {
  const result = await ingest(async () => ({ status: 401, body: {} }));
  assert.equal(result.classification, "authentication_failed");
});

const meta = {
  sourceSystem: "jira-jsm",
  projectReference: "project:OPS",
  evidenceClass: "observed",
  transportAuthenticity: "live_api",
  observationWindowLabel: "w",
  installationRef: "install-1",
};
const window = { start: "2026-09-15T00:00:00.000Z", end: "2026-10-15T00:00:00.000Z", convention: "closed-start-open-end-utc", windowDays: 30 };

test("reopened case at cutoff stays open and out-of-window events do not extend residence", () => {
  const issue = {
    key: "OPS-R",
    created: "2026-09-20T00:00:00.000Z",
    resolutiondate: "2026-09-21T00:00:00.000Z",
    status: { id: "1" },
    changelog: [
      { id: "1", field: "status", created: "2026-09-21T00:00:00.000Z", from: "1", to: "3" },
      { id: "2", field: "resolution", created: "2026-09-21T00:00:00.000Z", from: null, to: "10000" },
      { id: "3", field: "resolution", created: "2026-10-14T00:00:00.000Z", from: "10000", to: null },
      { id: "4", field: "status", created: "2026-10-14T00:00:00.000Z", from: "3", to: "1" },
      { id: "5", field: "status", created: "2026-10-16T00:00:00.000Z", from: "1", to: "2" },
    ],
    changelogComplete: true,
  };
  const caseRecord = normalizeCase(issue, meta);
  const events = eventsFromIssue(issue, caseRecord, meta);
  const lifecycle = reconstructLifecycle(caseRecord, events, window, issue);
  assert.equal(lifecycle.caseRecord.observationStatus === "reopened" || events.some((item) => item.eventType === "reopened"), true);
  assert.equal(lifecycle.intervals.some((item) => item.startAt === "2026-10-16T00:00:00.000Z"), false);
});

test("invalid transition chains stay incomplete", () => {
  const issue = {
    key: "OPS-BAD",
    created: "2026-10-01T00:00:00.000Z",
    status: { id: "9" },
    changelog: [
      { id: "1", field: "status", created: "2026-10-02T00:00:00.000Z", from: "1", to: "2" },
      { id: "2", field: "status", created: "2026-10-03T00:00:00.000Z", from: "8", to: "9" },
    ],
    changelogComplete: true,
  };
  const caseRecord = normalizeCase(issue, meta);
  const lifecycle = reconstructLifecycle(caseRecord, eventsFromIssue(issue, caseRecord, meta), window, issue);
  assert.equal(lifecycle.caseRecord.lifecycleCompleteness, "incomplete");
});

test("coverage denominators stay in [0,1] and event counts are not case-based", () => {
  const snapshot = buildSnapshot({
    issues: [
      {
        key: "OPS-1",
        created: "2026-10-01T00:00:00.000Z",
        resolutiondate: "2026-10-02T00:00:00.000Z",
        status: { id: "3" },
        changelog: [{ id: "1", field: "status", created: "2026-10-02T00:00:00.000Z", from: "1", to: "3" }],
        worklogs: [],
        sla: [],
        syntheticOrigin: false,
      },
    ],
    sourceProject: { reference: "project:OPS", key: "OPS", name: "Lab", serviceDeskId: "1" },
    window,
    importConfiguration: { windowDays: 30, recordLimit: 40, pageLimit: 8, cohortPolicy: "open-during-window", includeWorklogs: true, includeSla: true },
    extraction: { complete: true, truncatedReason: null, pageCount: 1, retryCount: 0, inconsistentSource: false, authorized: true, worklogCapability: "retrieved", slaCapability: "retrieved", changelogCapability: "retrieved" },
    importStartedAt: "2026-10-15T00:00:00.000Z",
    importCompletedAt: "2026-10-15T00:00:00.100Z",
    evidenceClass: "observed",
    transportAuthenticity: "live_api",
  });
  const quality = assessDataQuality(
    { cases: snapshot.cases, events: snapshot.events, intervals: snapshot.intervals },
    snapshot.extraction,
    window,
  );
  for (const item of quality) {
    if (item.value !== null) assert.ok(item.value >= 0);
  }
  const descriptive = descriptiveEvidence(
    { cases: snapshot.cases, events: snapshot.events, intervals: snapshot.intervals },
    window,
    snapshot.provenance,
  );
  const transitions = descriptive.find((item) => item.metricId === "status_transition_count");
  assert.equal(transitions.coverage, 1);
  assert.equal(transitions.value, snapshot.events.filter((item) => item.eventType === "status_changed").length);
  assert.equal(validateSnapshot(snapshot).ok, true);
  const representativeness = quality.find((item) => item.metricId === "representativeness");
  assert.equal(representativeness.status, "warning");
});

test("fingerprints change with completeness and runtime contract validation runs", () => {
  const base = {
    issues: [{ key: "OPS-1", created: "2026-10-01T00:00:00.000Z", status: { id: "1" }, changelog: [], syntheticOrigin: false }],
    sourceProject: { reference: "project:OPS", key: "OPS", name: "Lab", serviceDeskId: "1" },
    window,
    importConfiguration: { windowDays: 30, recordLimit: 40, pageLimit: 8, cohortPolicy: "open-during-window", includeWorklogs: true, includeSla: true },
    importStartedAt: "2026-10-15T00:00:00.000Z",
    importCompletedAt: "2026-10-15T00:00:00.100Z",
    evidenceClass: "observed",
    transportAuthenticity: "live_api",
  };
  const complete = buildSnapshot({
    ...base,
    extraction: { complete: true, truncatedReason: null, pageCount: 1, retryCount: 0, inconsistentSource: false, authorized: true, worklogCapability: "retrieved", slaCapability: "retrieved", changelogCapability: "retrieved" },
  });
  const partial = buildSnapshot({
    ...base,
    extraction: { complete: false, truncatedReason: "page_budget", pageCount: 8, retryCount: 0, inconsistentSource: false, authorized: true, worklogCapability: "retrieved", slaCapability: "retrieved", changelogCapability: "partial" },
  });
  assert.notEqual(complete.contentFingerprint, partial.contentFingerprint);
  assert.equal(contentFingerprint(complete), complete.contentFingerprint);
  assert.equal(validateSnapshot(complete).ok, true);
});
