import assert from "node:assert/strict";
import test from "node:test";
import { classifyJiraResponse, classifyNetworkFailure } from "./classify-response.js";

test("permission and authentication failures are distinct from empty datasets", () => {
  assert.equal(classifyJiraResponse(403, { issues: [] }, "issue-search").kind, "permission_denied");
  assert.equal(classifyJiraResponse(401, {}, "project").kind, "authentication_failed");
  assert.equal(classifyJiraResponse(200, { issues: [] }, "issue-search").kind, "empty");
  assert.equal(classifyJiraResponse(200, { values: [] }, "request-type-collection").kind, "empty");
});

test("a successful project HTTP status is not enough without required fields", () => {
  assert.equal(classifyJiraResponse(200, null, "project").kind, "malformed");
  assert.equal(classifyJiraResponse(200, {}, "project").kind, "malformed");
  assert.equal(classifyJiraResponse(200, { key: "OPS" }, "project").kind, "malformed");
  assert.equal(
    classifyJiraResponse(200, { id: "10000", key: "OPS", name: "OpsTwin IT Support Lab" }, "project").kind,
    "ok",
  );
});

test("collection envelopes require a values array even when empty", () => {
  assert.equal(classifyJiraResponse(200, {}, "request-type-collection").kind, "malformed");
  assert.equal(classifyJiraResponse(200, { values: [{ id: "1" }] }, "request-type-collection").kind, "malformed");
  assert.equal(
    classifyJiraResponse(200, { values: [{ id: "1", name: "Access" }] }, "request-type-collection").kind,
    "ok",
  );
  assert.equal(
    classifyJiraResponse(200, { values: [{ id: "1", projectKey: "OPS" }] }, "servicedesk-collection").kind,
    "ok",
  );
});

test("worklog and SLA envelopes reject empty objects", () => {
  assert.equal(classifyJiraResponse(200, {}, "worklog-collection").kind, "malformed");
  assert.equal(classifyJiraResponse(200, { worklogs: [] }, "worklog-collection").kind, "empty");
  assert.equal(classifyJiraResponse(200, { worklogs: [{ id: "1" }] }, "worklog-collection").kind, "ok");
  assert.equal(classifyJiraResponse(200, {}, "sla-collection").kind, "malformed");
  assert.equal(classifyJiraResponse(200, { values: [] }, "sla-collection").kind, "empty");
  assert.equal(classifyJiraResponse(200, { values: [{ id: "s" }] }, "sla-collection").kind, "ok");
  assert.equal(classifyJiraResponse(200, { values: [{ id: "h", created: "2026-01-01T00:00:00.000Z" }] }, "changelog-collection").kind, "ok");
  assert.equal(classifyJiraResponse(200, [], "project-statuses").kind, "empty");
  assert.equal(classifyJiraResponse(200, [{ id: "customfield_1" }], "field-metadata").kind, "ok");
});

test("malformed statuses, invalid JSON, rate limits, and 5xx stay explicit", () => {
  assert.equal(classifyJiraResponse("200", { key: "OPS" }, "project").kind, "malformed");
  assert.equal(classifyJiraResponse(200, "not-json", "project").kind, "malformed");
  assert.equal(classifyJiraResponse(429, {}, "project").kind, "rate_limited");
  assert.equal(classifyJiraResponse(404, {}, "project").kind, "not_found");
  assert.equal(classifyJiraResponse(503, {}, "project").kind, "upstream_failure");
  assert.equal(classifyNetworkFailure(new Error("socket timeout")).kind, "timeout");
  assert.equal(classifyNetworkFailure(new Error("ECONNRESET")).kind, "network_failure");
});
