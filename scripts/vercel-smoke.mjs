import { readFile } from "node:fs/promises";

const rawBase = process.argv[2] ?? process.env.VERCEL_PREVIEW_URL ?? "http://localhost:3000";
const base = rawBase.replace(/\/$/, "");
const fixture = JSON.parse(await readFile(new URL("../examples/product/support-operations-comparison.json", import.meta.url), "utf8"));
fixture.execution.runCount = 10;
fixture.scenarios = fixture.scenarios.slice(0, 1);

async function check(path, expected, init) {
  const started = performance.now();
  const response = await fetch(`${base}${path}`, init);
  const bytes = Number(response.headers.get("content-length") ?? 0);
  if (response.status !== expected) throw new Error(`${path}: expected ${expected}, received ${response.status}`);
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("json") ? await response.json() : await response.text();
  console.log(`${response.status} ${path} ${Math.round(performance.now() - started)}ms ${bytes || JSON.stringify(body).length}b`);
  return body;
}

const json = { "content-type": "application/json" };
await check("/", 200);
await check("/workspace", 200);
await check("/api/simulation/health", 200);
await check("/api/simulation/simulate", 200, { method: "POST", headers: json, body: JSON.stringify({ schemaVersion: "0.3.0", model: fixture.baselineModel, seedOverride: 7, resultDetail: { mode: "summary" } }) });
await check("/api/simulation/simulate/repeated", 200, { method: "POST", headers: json, body: JSON.stringify({ schemaVersion: "0.4.0", model: fixture.baselineModel, baseSeed: 7, runCount: 2, representativeRun: { detailMode: "summary", sampledItemLimit: null } }) });
const comparison = await check("/api/simulation/compare/scenarios", 200, { method: "POST", headers: json, body: JSON.stringify(fixture) });
if (comparison.integrity?.status !== "passed") throw new Error("Comparison integrity did not pass");
await check("/api/simulation/compare/scenarios", 422, { method: "POST", headers: json, body: "{}" });
const overBudget = structuredClone(fixture); overBudget.execution.runCount = 500; overBudget.baselineModel.sources[0].itemCount = 1000;
await check("/api/simulation/compare/scenarios", 422, { method: "POST", headers: json, body: JSON.stringify(overBudget) });
