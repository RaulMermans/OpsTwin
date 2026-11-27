const SCHEMA_VERSION = "os.1.0.0";
const COMPLETENESS = new Set(["complete", "partial", "empty", "invalid"]);
const READINESS = new Set(["valid", "partial", "invalid", "insufficient_for_calibration", "potentially_suitable_for_calibration_assessment"]);
const EVIDENCE = new Set(["observed", "derived", "assumed", "synthetic", "unknown"]);

function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fail(path, message) {
  return { ok: false, path, message };
}

function requireKeys(value, keys, path) {
  if (!isRecord(value)) return fail(path, "Expected an object.");
  for (const key of keys) {
    if (!(key in value)) return fail(`${path}.${key}`, "Missing required field.");
  }
  return null;
}

export function validateSnapshot(snapshot) {
  const root = requireKeys(snapshot, [
    "schemaVersion",
    "snapshotId",
    "connectorVersion",
    "sourceSystem",
    "sourceProject",
    "observationWindow",
    "importTimestamp",
    "importConfiguration",
    "cases",
    "events",
    "statuses",
    "requestTypes",
    "intervals",
    "descriptiveEvidence",
    "dataQuality",
    "completenessStatus",
    "readiness",
    "provenance",
    "contentFingerprint",
  ], "snapshot");
  if (root) return root;
  if (snapshot.schemaVersion !== SCHEMA_VERSION) return fail("schemaVersion", "Unsupported snapshot schema.");
  if (!COMPLETENESS.has(snapshot.completenessStatus)) return fail("completenessStatus", "Invalid completeness status.");
  if (!READINESS.has(snapshot.readiness)) return fail("readiness", "Invalid readiness.");
  if (!/^[a-f0-9]{64}$/.test(snapshot.contentFingerprint)) return fail("contentFingerprint", "Fingerprint must be 64 hex characters.");
  if (!EVIDENCE.has(snapshot.provenance?.evidenceClass)) return fail("provenance.evidenceClass", "Invalid evidence class.");
  if (!Array.isArray(snapshot.cases) || !Array.isArray(snapshot.events) || !Array.isArray(snapshot.intervals)) {
    return fail("cases", "Cases, events, and intervals must be arrays.");
  }
  if (snapshot.extraction && typeof snapshot.extraction.complete !== "boolean") {
    return fail("extraction.complete", "Extraction completeness must be boolean.");
  }
  for (const [index, item] of snapshot.cases.entries()) {
    const missing = requireKeys(item, ["caseId", "sourceReference", "lifecycleCompleteness", "observationStatus", "provenance"], `cases[${index}]`);
    if (missing) return missing;
    if (item.lifecycleCompleteness === "complete" && item.observationStatus === "unknown") {
      return fail(`cases[${index}].lifecycleCompleteness`, "Unknown observation cannot be a complete lifecycle.");
    }
  }
  return { ok: true, path: null, message: null };
}
