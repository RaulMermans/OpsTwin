import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { childEnvironment, nodeExecutable, pythonExecutable } from "./task-runtime.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const simulationApi = resolve(root, "apps", "simulation-api");
const python = pythonExecutable(root);
const pnpm = process.platform === "win32" ? "pnpm.cmd" : "pnpm";

function run(command, args, cwd = root) {
  const needsCommandShell = process.platform === "win32" && command.endsWith(".cmd");
  const executable = needsCommandShell ? (process.env.ComSpec ?? "cmd.exe") : command;
  const executableArgs = needsCommandShell ? ["/d", "/s", "/c", command, ...args] : args;
  const result = spawnSync(executable, executableArgs, {
    cwd,
    env: childEnvironment(),
    stdio: "inherit",
    shell: false,
  });
  if (result.error) {
    console.error(`Unable to start ${command}: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function requireEnvironment() {
  if (!existsSync(python)) {
    console.error("Missing .venv. Run `pnpm bootstrap` with Python 3.12 on PATH first.");
    process.exit(1);
  }
}

const tasks = {
  bootstrap() {
    if (!existsSync(python)) {
      const bootstrapPython = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3");
      run(bootstrapPython, ["-m", "venv", ".venv"]);
    }
    run(python, ["-m", "pip", "install", "--disable-pip-version-check", "-r", "apps/simulation-api/requirements.lock"]);
    run(python, ["-m", "pip", "install", "--no-deps", "-e", "apps/simulation-api"]);
    run(pnpm, ["install", "--frozen-lockfile"]);
  },
  "dev:web"() {
    run(pnpm, ["--filter", "@opstwin/web", "dev"]);
  },
  "dev:api"() {
    requireEnvironment();
    run(python, ["-m", "uvicorn", "app.main:app", "--reload"], simulationApi);
  },
  dev() {
    requireEnvironment();
    run(nodeExecutable(), ["scripts/dev-local.mjs"]);
  },
  "dev:vercel"() {
    run(pnpm, ["exec", "vercel", "dev", "-L"]);
  },
  "verify:vercel-runtime"() {
    run(nodeExecutable(), ["scripts/verify-vercel-runtime.mjs"]);
  },
  "build:vercel"() {
    tasks["verify:vercel-runtime"]();
    run(pnpm, ["exec", "vercel", "build"]);
  },
  "smoke:vercel-local"() {
    const url = process.argv.slice(3).find((arg) => arg !== "--");
    run(nodeExecutable(), ["scripts/vercel-smoke.mjs", url ?? "http://localhost:3000"]);
  },
  "smoke:preview"() {
    const url = process.argv.slice(3).find((arg) => arg !== "--");
    run(nodeExecutable(), ["scripts/vercel-smoke.mjs", url ?? process.env.VERCEL_PREVIEW_URL ?? ""]);
  },
  "smoke:local"() {
    requireEnvironment();
    run(nodeExecutable(), ["scripts/smoke-local.mjs"]);
  },
  "package:source"() {
    run(nodeExecutable(), ["scripts/package-source.mjs"]);
  },
  "verify:source-package"() {
    run(nodeExecutable(), ["scripts/verify-source-package.mjs"]);
  },
  "benchmark:playback"() {
    run(nodeExecutable(), ["scripts/benchmark-playback.mjs"]);
  },
  "run-example"() {
    requireEnvironment();
    run(python, ["-m", "app.cli", "../../examples/support-baseline.json"], simulationApi);
  },
  "benchmark:simulation"() {
    requireEnvironment();
    run(python, ["-m", "app.benchmark"], simulationApi);
  },
  "benchmark:smoke"() {
    requireEnvironment();
    run(python, ["-m", "app.benchmark", "--smoke"], simulationApi);
  },
  "benchmark:repeated"() {
    requireEnvironment();
    run(python, ["-m", "app.repeated_benchmark"], simulationApi);
  },
  "benchmark:repeated-smoke"() {
    requireEnvironment();
    run(python, ["-m", "app.repeated_benchmark", "--smoke"], simulationApi);
  },
  "benchmark:comparison"() {
    requireEnvironment();
    run(python, ["-m", "app.comparison_benchmark"], simulationApi);
  },
  "benchmark:comparison-smoke"() {
    requireEnvironment();
    run(python, ["-m", "app.comparison_benchmark", "--smoke"], simulationApi);
  },
  "benchmark:sensitivity"() {
    requireEnvironment();
    run(python, ["-m", "app.sensitivity_benchmark"], simulationApi);
  },
  "benchmark:sensitivity-smoke"() {
    requireEnvironment();
    run(python, ["-m", "app.sensitivity_benchmark", "--smoke"], simulationApi);
  },
  "benchmark:economics"() {
    requireEnvironment();
    run(python, ["-m", "app.economic_benchmark"], simulationApi);
  },
  "benchmark:economics-smoke"() {
    requireEnvironment();
    run(python, ["-m", "app.economic_benchmark", "--smoke"], simulationApi);
  },
  "benchmark:economic-sensitivity"() {
    requireEnvironment();
    run(python, ["-m", "app.economic_sensitivity_benchmark"], simulationApi);
  },
  "benchmark:economic-sensitivity-smoke"() {
    requireEnvironment();
    run(python, ["-m", "app.economic_sensitivity_benchmark", "--smoke"], simulationApi);
  },
  "verify:node-portability"() {
    run(nodeExecutable(), ["scripts/verify-node-portability.mjs"]);
  },
  lint() {
    requireEnvironment();
    run(python, ["-m", "ruff", "check", "apps/simulation-api"]);
    run(pnpm, ["--filter", "@opstwin/web", "lint"]);
  },
  typecheck() {
    requireEnvironment();
    run(python, ["-m", "mypy", "app"], simulationApi);
    run(pnpm, ["--filter", "@opstwin/web", "typecheck"]);
  },
  test() {
    requireEnvironment();
    run(python, ["-m", "pytest", "apps/simulation-api/tests"]);
    tasks["test:web"]();
  },
  "test:web"() {
    run(pnpm, ["--filter", "@opstwin/web", "test"]);
  },
  build() {
    requireEnvironment();
    run(python, ["-m", "build", "--outdir", "../../dist/simulation-api"], simulationApi);
    run(pnpm, ["--filter", "@opstwin/web", "build"]);
  },
  verify() {
    tasks["verify:node-portability"]();
    tasks["verify:vercel-runtime"]();
    tasks.lint();
    tasks.typecheck();
    tasks.test();
    tasks.build();
    tasks["run-example"]();
    tasks["benchmark:smoke"]();
    tasks["benchmark:repeated-smoke"]();
    tasks["benchmark:comparison-smoke"]();
    tasks["benchmark:sensitivity-smoke"]();
    tasks["benchmark:economics-smoke"]();
    tasks["benchmark:economic-sensitivity-smoke"]();
    tasks["package:source"]();
    tasks["verify:source-package"]();
  },
};

const taskName = process.argv[2];
if (!(taskName in tasks)) {
  console.error(`Unknown task: ${taskName ?? "<missing>"}`);
  process.exit(1);
}
tasks[taskName]();
