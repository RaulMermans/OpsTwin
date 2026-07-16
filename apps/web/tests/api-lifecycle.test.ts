import { afterEach, describe, expect, it, vi } from "vitest";

import { runScenarioComparison } from "../lib/api/simulation";

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

describe("comparison request lifecycle", () => {
  it("distinguishes a user abort", async () => {
    vi.stubGlobal("fetch", vi.fn((_path, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    })));
    const controller = new AbortController(); const request = runScenarioComparison({}, controller.signal); controller.abort();
    await expect(request).rejects.toMatchObject({ code: "CANCELLED", message: "The browser stopped waiting for this comparison. The server may still finish processing the request." });
  });

  it("distinguishes the browser timeout and preserves-input wording", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_path, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    })));
    const request = runScenarioComparison({}); await vi.advanceTimersByTimeAsync(60_000);
    await expect(request).rejects.toMatchObject({ code: "TIMEOUT", message: "The comparison took longer than the browser waiting limit. Your inputs have been preserved." });
  });

  it("maps malformed success JSON to an unexpected response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue({ schemaVersion: "unknown" }) }));
    await expect(runScenarioComparison({})).rejects.toMatchObject({ code: "UNEXPECTED_RESPONSE" });
  });

  it("maps network failures without leaking the exception", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("private network details")));
    await expect(runScenarioComparison({})).rejects.toMatchObject({ code: "NETWORK_ERROR", message: "The simulation service could not be reached. Your inputs have been preserved." });
  });
});
