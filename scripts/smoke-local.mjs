import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { createServer } from "node:net";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { childEnvironment, pythonExecutable } from "./task-runtime.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const simulationApi = resolve(root, "apps", "simulation-api");
const web = resolve(root, "apps", "web");
const python = pythonExecutable(root);
const nextBin = resolve(web, "node_modules", ".bin", process.platform === "win32" ? "next.cmd" : "next");
const host = "127.0.0.1";
const webPort = Number(process.env.OPSTWIN_WEB_PORT ?? 3000);
const apiPort = Number(process.env.OPSTWIN_API_PORT ?? 8000);
const base = `http://${host}:${webPort}`;

function checkPortFree(port) {
  return new Promise((resolvePort, rejectPort) => {
    const server = createServer();
    server.once("error", (error) => {
      if (error.code === "EADDRINUSE") rejectPort(new Error(`Port ${port} is already in use.`));
      else rejectPort(error);
    });
    server.once("listening", () => server.close(() => resolvePort()));
    server.listen(port, host);
  });
}

async function waitFor(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // service not ready yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function check(path, expected, init) {
  const started = performance.now();
  const response = await fetch(`${base}${path}`, init);
  if (response.status !== expected) {
    throw new Error(`${path}: expected ${expected}, received ${response.status}`);
  }
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("json") ? await response.json() : await response.text();
  console.log(`${response.status} ${path} ${Math.round(performance.now() - started)}ms`);
  return body;
}

async function main() {
  await checkPortFree(webPort);
  await checkPortFree(apiPort);

  const apiChild = spawn(
    python,
    ["-m", "uvicorn", "app.main:app", "--host", host, "--port", String(apiPort)],
    { cwd: simulationApi, env: childEnvironment(), stdio: "inherit" },
  );
  const webChild = spawn(nextBin, ["dev", "--port", String(webPort)], {
    cwd: web,
    env: { ...childEnvironment(), OPSTWIN_DEV_API_ORIGIN: `http://${host}:${apiPort}` },
    stdio: "inherit",
    shell: process.platform === "win32",
  });

  const stop = () => {
    for (const child of [apiChild, webChild]) if (!child.killed) child.kill("SIGTERM");
  };

  try {
    await waitFor(`http://${host}:${apiPort}/api/simulation/health`, 30000);
    await waitFor(`${base}/`, 60000);

    const comparisonFixture = JSON.parse(
      await readFile(resolve(root, "examples/product/support-operations-comparison.json"), "utf8"),
    );
    comparisonFixture.comparison.execution.runCount = 4;
    comparisonFixture.comparison.scenarios = comparisonFixture.comparison.scenarios.slice(0, 1);
    const sensitivityFixture = JSON.parse(
      await readFile(resolve(root, "examples/product/support-sensitivity-request.json"), "utf8"),
    );
    const economicsFixture = JSON.parse(
      await readFile(resolve(root, "examples/product/support-economic-comparison-request.json"), "utf8"),
    );
    economicsFixture.comparison.execution.runCount = 2;

    const json = { "content-type": "application/json" };
    await check("/", 200);
    await check("/workspace", 200);
    await check("/api/simulation/health", 200);
    const comparison = await check("/api/simulation/compare/scenarios", 200, {
      method: "POST",
      headers: json,
      body: JSON.stringify(comparisonFixture.comparison),
    });
    if (comparison.integrity?.status !== "passed") throw new Error("comparison integrity did not pass");
    const sensitivity = await check("/api/simulation/analyze/sensitivity", 200, {
      method: "POST",
      headers: json,
      body: JSON.stringify(sensitivityFixture),
    });
    if (sensitivity.integrity?.status !== "passed") throw new Error("sensitivity integrity did not pass");
    const economics = await check("/api/simulation/analyze/economics", 200, {
      method: "POST",
      headers: json,
      body: JSON.stringify(economicsFixture),
    });
    if (economics.integrity?.status !== "passed") throw new Error("economics integrity did not pass");

    console.log("Local smoke passed: same-origin routing, no manual API-origin configuration.");
  } finally {
    stop();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
