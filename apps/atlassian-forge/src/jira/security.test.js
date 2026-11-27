import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { rejectBrowserProjectSubstitution, installationRefFromContext } from "./context.js";

const index = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../index.js"), "utf8");
const ingest = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "./ingest.js"), "utf8");

test("resolver constructor uses Forge default-export interop", () => {
  assert.match(index, /typeof ResolverModule === "function"/);
});

test("operational import never uses asApp and never forwards issues to the simulation remote", () => {
  assert.match(index, /importOperationalSnapshot/);
  assert.doesNotMatch(index, /asApp\(/);
  assert.doesNotMatch(index, /invokeRemote\(REMOTE_KEY, \{[\s\S]*snapshot/);
  assert.match(index, /contractVersion: "cg1.v1"/);
  assert.doesNotMatch(ingest, /asApp\(/);
  assert.doesNotMatch(ingest, /description/);
  assert.doesNotMatch(ingest, /comment/);
});

test("installation refs are distinct from browser project identity", () => {
  assert.equal(installationRefFromContext({ installation: { id: "ari:cloud:ecosystem::installation/b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815" } }).includes("b1bb872d"), true);
  assert.equal(rejectBrowserProjectSubstitution({ extension: { project: { key: "OPS" } } }, { projectKey: "OPS" }), null);
});

test("simulation adapter file is not imported by the Forge ingest path", () => {
  assert.equal(ingest.includes("remote_compare"), false);
  assert.equal(index.includes("/api/simulation/"), false);
});
