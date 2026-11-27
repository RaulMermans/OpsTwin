import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { REGISTERED_APP_ID, isAppAri } from "./app-identity.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = readFileSync(resolve(root, "manifest.yml"), "utf8");
const appIdMatch = manifest.match(/ari:cloud:ecosystem::app\/[0-9a-f-]{36}/i);

test("manifest binds the registered OpsTwin app identity and least-privilege scopes", () => {
  assert.ok(appIdMatch);
  assert.equal(isAppAri(appIdMatch[0]), true);
  assert.equal(appIdMatch[0], REGISTERED_APP_ID);
  assert.match(manifest, /jiraServiceManagement:queuePage:/);
  assert.match(manifest, /jira:projectPage:/);
  assert.match(manifest, /title: OpsTwin for Jira/);
  assert.match(manifest, /path: static\/transformation-lab\/build/);
  assert.match(manifest, /name: nodejs22\.x/);
  assert.match(manifest, /read:jira-work/);
  assert.match(manifest, /read:servicedesk-request/);
  assert.doesNotMatch(manifest, /manage:/);
  assert.doesNotMatch(manifest, /write:/);
  assert.doesNotMatch(manifest, /read:app-user-token/);
  assert.doesNotMatch(manifest, /read:app-system-token/);
});

test("manifest declares a compute-only remote without OAuth token forwarding", () => {
  assert.match(manifest, /^remotes:/m);
  assert.match(manifest, /key: opstwin-simulation/);
  assert.match(manifest, /baseUrl: https:\/\/ops-twin\.vercel\.app/);
  assert.match(manifest, /- compute/);
  assert.match(manifest, /remote: opstwin-simulation/);
  assert.doesNotMatch(manifest, /FORGE_API_TOKEN/);
  assert.doesNotMatch(manifest, /clientSecret/);
  assert.match(manifest, /appUserToken:\s*\n\s+enabled: false/);
  assert.match(manifest, /appSystemToken:\s*\n\s+enabled: false/);
});
