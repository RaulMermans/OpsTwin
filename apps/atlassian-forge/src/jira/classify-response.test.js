import assert from "node:assert/strict";
import test from "node:test";
import { classifyJiraResponse } from "./classify-response.js";

test("permission failures are distinct from empty datasets", () => {
  assert.equal(classifyJiraResponse(403, { issues: [] }).kind, "permission_denied");
  assert.equal(classifyJiraResponse(401, {}).kind, "permission_denied");
  assert.equal(classifyJiraResponse(200, { issues: [], total: 0 }).kind, "empty");
  assert.equal(classifyJiraResponse(200, { values: [] }).kind, "empty");
});

test("successful objects are not treated as empty", () => {
  assert.equal(classifyJiraResponse(200, { id: "10000", key: "OPS", name: "OpsTwin IT Support Lab" }).kind, "ok");
});

test("malformed statuses and bodies are rejected", () => {
  assert.equal(classifyJiraResponse("200", { key: "OPS" }).kind, "malformed");
  assert.equal(classifyJiraResponse(200, "not-json").kind, "malformed");
});

test("rate limits and missing resources stay explicit", () => {
  assert.equal(classifyJiraResponse(429, {}).kind, "rate_limited");
  assert.equal(classifyJiraResponse(404, {}).kind, "not_found");
});
