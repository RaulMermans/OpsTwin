import assert from "node:assert/strict";
import test from "node:test";
import { spawnSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const script = resolve(dirname(fileURLToPath(import.meta.url)), "../../../../scripts/jira-sandbox-fixtures.mjs");

test("sandbox fixture tool rejects the wrong site and stays dry-run", () => {
  const rejected = spawnSync("node", [script, "--site", "evil.atlassian.net", "--project", "OPS"], { encoding: "utf8" });
  assert.equal(rejected.status, 2);
  const dry = spawnSync("node", [script, "--site", "opstwin-dev.atlassian.net", "--project", "OPS", "--count", "3"], { encoding: "utf8" });
  assert.equal(dry.status, 0);
  assert.match(dry.stdout, /Dry-run only/);
  const execute = spawnSync("node", [script, "--site", "opstwin-dev.atlassian.net", "--project", "OPS", "--execute"], { encoding: "utf8" });
  assert.equal(execute.status, 2);
});
