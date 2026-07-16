import assert from "node:assert/strict";
import { dirname, delimiter } from "node:path";
import { spawnSync } from "node:child_process";

import { childEnvironment, nodeExecutable } from "./task-runtime.mjs";

assert.equal(nodeExecutable(), process.execPath);

const inherited = { ...process.env, PATH: "C:\\Windows\\System32" };
const environment = childEnvironment(inherited);
assert.equal(environment.PATH.split(delimiter)[0], dirname(process.execPath));

const child = spawnSync(nodeExecutable(), ["-p", "process.execPath"], {
  encoding: "utf8",
  env: environment,
  shell: false,
});
assert.equal(child.status, 0, child.stderr);
assert.equal(child.stdout.trim(), process.execPath);
console.log("Node child portability check passed");
