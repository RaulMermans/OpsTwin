import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = readFileSync(resolve(root, "manifest.yml"), "utf8");

test("manifest declares the CG-0 JSM queue page and Custom UI resource", () => {
  assert.match(manifest, /jiraServiceManagement:queuePage:/);
  assert.match(manifest, /jira:projectPage:/);
  assert.match(manifest, /title: OpsTwin for Jira/);
  assert.match(manifest, /path: static\/transformation-lab\/build/);
  assert.match(manifest, /name: nodejs22\.x/);
  assert.match(manifest, /ari:cloud:ecosystem::app\/73670daa-a329-4491-8a96-89bf239b203b/);
  assert.match(manifest, /read:jira-work/);
  assert.match(manifest, /read:servicedesk-request/);
  assert.doesNotMatch(manifest, /manage:/);
  assert.doesNotMatch(manifest, /write:/);
});

test("manifest does not declare live remotes or secrets", () => {
  assert.doesNotMatch(manifest, /^remotes:/m);
  assert.doesNotMatch(manifest, /FORGE_API_TOKEN/);
  assert.doesNotMatch(manifest, /clientSecret/);
});
