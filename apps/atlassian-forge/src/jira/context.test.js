import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../index.js"), "utf8");

test("resolver refuses browser-supplied project substitution", () => {
  assert.match(source, /untrusted_project/);
  assert.match(source, /projectKeyFromContext/);
  assert.match(source, /api\.asUser\(\)/);
  assert.doesNotMatch(source, /payload\.projectKey \|\|/);
});
