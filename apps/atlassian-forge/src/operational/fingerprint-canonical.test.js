import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { contentFingerprint } from "./fingerprint.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "../../../../");
const cases = JSON.parse(
  readFileSync(join(root, "contracts/examples/canonical-fingerprint/cases.json"), "utf8"),
);
const expected = JSON.parse(
  readFileSync(join(root, "contracts/examples/canonical-fingerprint/expected.json"), "utf8"),
);

test("python and javascript fingerprints match golden cases", () => {
  for (const [name, snapshot] of Object.entries(cases)) {
    assert.equal(contentFingerprint(snapshot), expected[name], name);
  }
  assert.equal(contentFingerprint(cases.nested_a), contentFingerprint(cases.nested_b));
  assert.equal(contentFingerprint(cases.volatile_a), contentFingerprint(cases.volatile_b));
  assert.notEqual(contentFingerprint(cases.completeness_complete), contentFingerprint(cases.completeness_partial));
  assert.notEqual(contentFingerprint(cases.origin_synthetic), contentFingerprint(cases.origin_observed));
});
