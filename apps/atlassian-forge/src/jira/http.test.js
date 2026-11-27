import assert from "node:assert/strict";
import test from "node:test";
import { fetchWithRetry } from "./http.js";

test("401 and 403 stop immediately", async () => {
  const unauthorized = await fetchWithRetry(async () => ({ status: 401, body: {} }), { sleep: async () => {} });
  assert.equal(unauthorized.stopped, "authorization");
  const forbidden = await fetchWithRetry(async () => ({ status: 403, body: {} }), { sleep: async () => {} });
  assert.equal(forbidden.stopped, "authorization");
});

test("429 retries then exhausts", async () => {
  let calls = 0;
  const result = await fetchWithRetry(
    async () => {
      calls += 1;
      return { status: 429, headers: { "retry-after": "0" }, body: {} };
    },
    { maxRetries: 2, sleep: async () => {} },
  );
  assert.equal(calls, 3);
  assert.equal(result.stopped, "retry_exhausted");
});

test("Retry-After longer than the remaining budget does not retry", async () => {
  let calls = 0;
  const result = await fetchWithRetry(
    async () => {
      calls += 1;
      return { status: 429, headers: { "retry-after": "30" }, body: {} };
    },
    { maxRetries: 3, remainingMs: 1000, sleep: async () => {} },
  );
  assert.equal(calls, 1);
  assert.equal(result.stopped, "retry_exceeds_deadline");
});

test("5xx recovers and malformed network retries", async () => {
  let calls = 0;
  const recovered = await fetchWithRetry(
    async () => {
      calls += 1;
      if (calls === 1) return { status: 503, body: {} };
      return { status: 200, body: { ok: true } };
    },
    { maxRetries: 2, sleep: async () => {} },
  );
  assert.equal(recovered.status, 200);
  const timeout = await fetchWithRetry(
    async () => ({ status: 0, networkError: true }),
    { maxRetries: 0, sleep: async () => {} },
  );
  assert.equal(timeout.networkError, true);
});
