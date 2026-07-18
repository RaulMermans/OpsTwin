import { createServer } from "node:net";
import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { childEnvironment, pythonExecutable } from "./task-runtime.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const simulationApi = resolve(root, "apps", "simulation-api");
const web = resolve(root, "apps", "web");
const python = pythonExecutable(root);
const nextBin = resolve(web, "node_modules", ".bin", process.platform === "win32" ? "next.cmd" : "next");

const webPort = Number(process.env.OPSTWIN_WEB_PORT ?? 3000);
const apiPort = Number(process.env.OPSTWIN_API_PORT ?? 8000);
const host = "127.0.0.1";

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

async function main() {
  for (const port of [webPort, apiPort]) {
    await checkPortFree(port);
  }

  const children = [];
  let shuttingDown = false;

  function shutdown(code) {
    if (shuttingDown) return;
    shuttingDown = true;
    for (const child of children) {
      if (!child.killed) child.kill("SIGTERM");
    }
    process.exitCode = code ?? 0;
  }

  const apiChild = spawn(
    python,
    ["-m", "uvicorn", "app.main:app", "--reload", "--host", host, "--port", String(apiPort)],
    { cwd: simulationApi, env: childEnvironment(), stdio: "inherit" },
  );
  children.push(apiChild);

  const webEnv = {
    ...childEnvironment(),
    OPSTWIN_DEV_API_ORIGIN: `http://${host}:${apiPort}`,
  };
  const webChild = spawn(nextBin, ["dev", "--port", String(webPort)], {
    cwd: web,
    env: webEnv,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  children.push(webChild);

  for (const child of children) {
    child.on("exit", (code) => {
      if (!shuttingDown) {
        console.log(`A development process exited (code ${code}); stopping the other process.`);
        shutdown(code ?? 1);
      }
    });
  }

  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => shutdown(0));
  }

  console.log(`Web    -> http://${host}:${webPort}`);
  console.log(`API    -> http://${host}:${apiPort}/api/simulation`);
  console.log(`Health -> http://${host}:${apiPort}/api/simulation/health`);
  console.log("OPSTWIN_DEV_API_ORIGIN configured automatically; press Ctrl+C to stop both.");
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
