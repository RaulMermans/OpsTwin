import assert from "node:assert/strict";
import test from "node:test";
import { ingestOperationalData } from "./ingest.js";
import { rejectBrowserProjectSubstitution } from "./context.js";

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

const projectOk = { status: 200, body: { id: "10000", key: "OPS", name: "OpsTwin IT Support Lab", projectTypeKey: "service_desk" } };
const desksOk = { status: 200, body: { values: [{ id: "1", projectKey: "OPS" }] } };
const typesOk = { status: 200, body: { values: [{ id: "10", name: "Get IT help" }] } };
const fieldsOk = { status: 200, body: [{ id: "customfield_1", name: "Request Type", schema: { custom: "com.atlassian.servicedesk:vp-origin" } }] };
const statusesOk = { status: 200, body: [{ statuses: [{ id: "1", name: "Open", statusCategory: { key: "new" } }] }] };

function baseHandlers(search) {
  return [
    ["/rest/api/3/project/OPS", projectOk],
    ["/rest/servicedeskapi/servicedesk/1/requesttype", typesOk],
    ["/rest/servicedeskapi/servicedesk", desksOk],
    ["/rest/api/3/field", fieldsOk],
    ["/rest/api/3/project/OPS/statuses", statusesOk],
    ["/rest/api/3/search/jql", search],
    ["/rest/api/3/issue/", { status: 200, body: { values: [], total: 0, isLastPage: true } }],
    ["/rest/servicedeskapi/request/", { status: 200, body: { values: [] } }],
  ];
}

test("browser-supplied project keys are rejected before ingest", () => {
  const blocked = rejectBrowserProjectSubstitution({ extension: { project: { key: "OPS" } } }, { projectKey: "SECRET" });
  assert.equal(blocked.kind, "untrusted_project");
});

test("authorized empty search is a valid empty snapshot", async () => {
  const result = await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: { windowDays: 30, projectKey: "OPS" },
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: router(baseHandlers({ status: 200, body: { issues: [], isLast: true } })),
  });
  assert.equal(result.status, "completed");
  assert.equal(result.snapshot.completenessStatus, "empty");
  assert.equal(result.snapshot.cases.length, 0);
});

test("malformed successful search is not an empty dataset", async () => {
  const result = await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: { windowDays: 30 },
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: router(baseHandlers({ status: 200, body: { values: [] } })),
  });
  assert.equal(result.status, "failed");
  assert.equal(result.classification, "malformed");
});

test("401 and 403 fail closed", async () => {
  const unauthorized = await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: {},
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: async () => ({ status: 401, body: {} }),
  });
  assert.equal(unauthorized.classification, "authentication_failed");
  const forbidden = await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: {},
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: async () => ({ status: 403, body: {} }),
  });
  assert.equal(forbidden.classification, "permission_denied");
});

test("project-scoped search rejects records from another project", async () => {
  const result = await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: { windowDays: 30 },
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: router(
      baseHandlers({
        status: 200,
        body: {
          issues: [
            {
              id: "9",
              key: "OTHER-1",
              fields: {
                created: "2026-10-01T00:00:00.000Z",
                project: { key: "OTHER" },
                status: { id: "1", name: "Open", statusCategory: { key: "new" } },
              },
            },
          ],
          isLast: true,
        },
      }),
    ),
  });
  assert.equal(result.snapshot.cases.length, 0);
});

test("payload projectKey cannot redirect the trusted project", async () => {
  const paths = [];
  await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: { windowDays: 30, projectKey: "EVIL" },
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: async (path) => {
      paths.push(path);
      return router(baseHandlers({ status: 200, body: { issues: [], isLast: true } }))(path);
    },
  });
  assert.ok(paths.some((path) => path.includes("/project/OPS")));
  assert.equal(paths.some((path) => path.includes("/project/EVIL")), false);
  assert.ok(paths.some((path) => path.includes("jql=") && path.includes("OPS")));
});

test("live-shaped issue search normalizes a snapshot with provenance", async () => {
  const result = await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: { windowDays: 30 },
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: router([
      ...baseHandlers({
        status: 200,
        body: {
          issues: [
            {
              id: "100",
              key: "OPS-1",
              changelog: {
                histories: [
                  {
                    id: "h1",
                    created: "2026-10-02T00:00:00.000Z",
                    items: [{ field: "status", from: "1", to: "3" }],
                  },
                ],
              },
              fields: {
                created: "2026-10-01T00:00:00.000Z",
                resolutiondate: "2026-10-02T00:00:00.000Z",
                updated: "2026-10-02T00:00:00.000Z",
                project: { key: "OPS" },
                status: { id: "3", name: "Done", statusCategory: { key: "done" } },
                priority: { id: "2", name: "High" },
                assignee: { accountId: "abc" },
                customfield_1: { requestType: { id: "10" } },
                labels: ["opstwin-synthetic"],
              },
            },
          ],
          isLast: true,
        },
      }),
      ["/rest/api/3/issue/OPS-1/worklog", { status: 200, body: { worklogs: [{ id: "w", started: "2026-10-01T03:00:00.000Z", timeSpentSeconds: 120 }], total: 1, isLastPage: true } }],
      ["/rest/servicedeskapi/request/OPS-1/sla", { status: 200, body: { values: [{ id: "s", name: "Time to resolution", completedCycles: [{ startTime: { iso8601: "2026-10-01T00:00:00.000Z" }, stopTime: { iso8601: "2026-10-02T00:00:00.000Z" }, elapsedTime: { millis: 86400000 }, breached: false }] }] } }],
    ]),
  });
  assert.equal(result.status, "completed");
  assert.equal(result.snapshot.cases.length, 1);
  assert.equal(result.snapshot.cases[0].provenance.evidenceClass, "synthetic");
  assert.equal(result.snapshot.provenance.transportAuthenticity, "live_api");
  assert.ok(result.snapshot.events.some((item) => item.eventType === "status_changed"));
  assert.ok(result.snapshot.events.some((item) => item.eventType === "worklog_recorded"));
  assert.ok(result.snapshot.events.some((item) => item.eventType === "sla_cycle_observed"));
  assert.equal(result.snapshot.cases[0].assigneeReference.startsWith("ref_"), true);
});

test("unsupported window is rejected", async () => {
  const result = await ingestOperationalData({
    projectKey: "OPS",
    installationRef: "install-1",
    payload: { windowDays: 7 },
    now: new Date("2026-10-15T00:00:00.000Z"),
    requestJson: async () => ({ status: 200, body: {} }),
  });
  assert.equal(result.classification, "invalid_configuration");
});
