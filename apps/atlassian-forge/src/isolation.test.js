import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

test("simulation API does not import Atlassian or Forge modules", () => {
  const pyproject = readFileSync(resolve(repoRoot, "apps/simulation-api/pyproject.toml"), "utf8");
  assert.doesNotMatch(pyproject, /forge/i);
  assert.doesNotMatch(pyproject, /atlassian/i);
  const main = readFileSync(resolve(repoRoot, "apps/simulation-api/app/main.py"), "utf8");
  assert.doesNotMatch(main, /atlassian/);
  assert.doesNotMatch(main, /forge/);
});

test("web transport remains same-origin simulation contracts", () => {
  const transport = readFileSync(resolve(repoRoot, "apps/web/lib/api/simulation.ts"), "utf8");
  assert.match(transport, /\/api\/simulation\/compare\/scenarios/);
  assert.doesNotMatch(transport, /@forge\//);
});
