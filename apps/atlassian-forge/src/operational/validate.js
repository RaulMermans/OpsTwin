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

const CASE_KEYS = [
  "schemaVersion",
  "caseId",
  "sourceReference",
  "sourceSystem",
  "projectReference",
  "requestTypeReference",
  "priorityReference",
  "createdAt",
  "resolvedAt",
  "currentStatusReference",
  "observationStatus",
  "lifecycleCompleteness",
  "provenance",
];
const EVENT_KEYS = ["eventId", "caseId", "eventType", "occurredAt", "observedAt", "previousValue", "newValue", "sourceReference", "provenance"];
const INTERVAL_KEYS = ["intervalId", "caseId", "intervalType", "startAt", "endAt", "durationMinutes", "censoring", "complete"];
const STATUS_KEYS = ["statusId", "displayName", "sourceCategory", "operationalClass", "mappingStatus", "classificationProvenance"];
const METRIC_KEYS = [
  "metricId",
  "definition",
  "value",
  "unit",
  "population",
  "sampleSize",
  "observationWindow",
  "excludedRecords",
  "coverage",
  "provenance",
  "interpretationLimitations",
];
const QUALITY_KEYS = ["metricId", "definition", "numerator", "denominator", "value", "status", "explanation", "consequence", "recommendedNextAction"];
const PROVENANCE_KEYS = ["sourceSystem", "evidenceClass", "transformationVersion"];

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
  const provenance = requireKeys(snapshot.provenance, PROVENANCE_KEYS, "provenance");
  if (provenance) return provenance;
  if (!EVIDENCE.has(snapshot.provenance.evidenceClass)) return fail("provenance.evidenceClass", "Invalid evidence class.");
  const window = requireKeys(snapshot.observationWindow, ["start", "end", "convention"], "observationWindow");
  if (window) return window;
  if (snapshot.observationWindow.convention !== "closed-start-open-end-utc") {
    return fail("observationWindow.convention", "Unsupported window convention.");
  }
  const importConfig = requireKeys(
    snapshot.importConfiguration,
    ["windowDays", "recordLimit", "pageLimit", "cohortPolicy", "includeWorklogs", "includeSla"],
    "importConfiguration",
  );
  if (importConfig) return importConfig;
  if (!Array.isArray(snapshot.cases) || !Array.isArray(snapshot.events) || !Array.isArray(snapshot.intervals)) {
    return fail("cases", "Cases, events, and intervals must be arrays.");
  }
  if (snapshot.extraction && typeof snapshot.extraction.complete !== "boolean") {
    return fail("extraction.complete", "Extraction completeness must be boolean.");
  }
  for (const [index, item] of snapshot.cases.entries()) {
    const missing = requireKeys(item, CASE_KEYS, `cases[${index}]`);
    if (missing) return missing;
    if (item.schemaVersion !== SCHEMA_VERSION) return fail(`cases[${index}].schemaVersion`, "Unsupported snapshot schema.");
    const caseProv = requireKeys(item.provenance, PROVENANCE_KEYS, `cases[${index}].provenance`);
    if (caseProv) return caseProv;
    if (item.lifecycleCompleteness === "complete" && item.observationStatus === "unknown") {
      return fail(`cases[${index}].lifecycleCompleteness`, "Unknown observation cannot be a complete lifecycle.");
    }
  }
  for (const [index, item] of snapshot.events.entries()) {
    const missing = requireKeys(item, EVENT_KEYS, `events[${index}]`);
    if (missing) return missing;
  }
  for (const [index, item] of snapshot.intervals.entries()) {
    const missing = requireKeys(item, INTERVAL_KEYS, `intervals[${index}]`);
    if (missing) return missing;
  }
  for (const [index, item] of snapshot.statuses.entries()) {
    const missing = requireKeys(item, STATUS_KEYS, `statuses[${index}]`);
    if (missing) return missing;
  }
  for (const [index, item] of snapshot.descriptiveEvidence.entries()) {
    const missing = requireKeys(item, METRIC_KEYS, `descriptiveEvidence[${index}]`);
    if (missing) return missing;
  }
  for (const [index, item] of snapshot.dataQuality.entries()) {
    const missing = requireKeys(item, QUALITY_KEYS, `dataQuality[${index}]`);
    if (missing) return missing;
  }
  return { ok: true, path: null, message: null };
}
