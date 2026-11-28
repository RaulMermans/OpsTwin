import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { rejectBrowserProjectSubstitution, installationRefFromContext } from "./context.js";

const index = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../index.js"), "utf8");
const ingest = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "./ingest.js"), "utf8");
const classify = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "./classify-response.js"), "utf8");

test("resolver constructor uses Forge default-export interop", () => {
  assert.match(index, /typeof ResolverModule === "function"/);
});

test("jira baseline construction re-extracts and does not trust browser snapshots", () => {
  const constructBlock = index.slice(index.indexOf('resolver.define("constructBaseline"'));
  assert.match(constructBlock, /trustedExtraction = true/);
  assert.match(constructBlock, /ingestOperationalData/);
  assert.match(constructBlock, /observationWindow/);
  assert.doesNotMatch(constructBlock, /payload\.snapshot/);
});

test("sensitive artifact operations fail closed without a verified user identity", () => {
  assert.match(index, /missing_principal/);
  assert.match(classify, /unauthorized_source/);
  assert.match(index, /currentSourceAccessDecision/);
  assert.doesNotMatch(index, /: "scope:installation-user-context"/);
});

test("signed evidence operations recheck current project access regardless of browser sourceMode", () => {
  const transform = index.slice(index.indexOf('resolver.define("runTransformationExperiment"'), index.indexOf('resolver.define("runEconomicEvaluation"'));
  const economics = index.slice(index.indexOf('resolver.define("runEconomicEvaluation"'), index.indexOf('resolver.define("constructBaseline"'));
  const construct = index.slice(index.indexOf('resolver.define("constructBaseline"'));
  assert.match(transform, /requireCurrentSourceAccess/);
  assert.match(economics, /requireCurrentSourceAccess/);
  assert.match(construct, /requireCurrentSourceAccess/);
  assert.doesNotMatch(transform, /if \(sourceMode === "jira"\)/);
  assert.doesNotMatch(economics, /if \(payload\.sourceMode === "jira"\)/);
  assert.equal(transform.split("catch (error)").length >= 3, true);
  assert.equal(economics.split("catch (error)").length >= 3, true);
});

test("operational import never uses asApp and never forwards issues to the simulation remote", () => {
  assert.match(index, /importOperationalSnapshot/);
  assert.doesNotMatch(index, /asApp\(/);
  const compareBlock = index.slice(index.indexOf("runSyntheticComparison"), index.indexOf("runSyntheticCalibration"));
  assert.doesNotMatch(compareBlock, /snapshot/);
  assert.match(index, /minimizeSnapshot/);
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
