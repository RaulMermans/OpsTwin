import { createHash } from "node:crypto";

const VOLATILE = new Set([
  "snapshotId",
  "importTimestamp",
  "importStartedAt",
  "importCompletedAt",
  "extractionTimestamp",
  "observedAt",
]);

export function canonicalize(value) {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(canonicalize);
  const keys = Object.keys(value)
    .filter((key) => !VOLATILE.has(key))
    .sort();
  const out = {};
  for (const key of keys) out[key] = canonicalize(value[key]);
  return out;
}

export function contentFingerprint(snapshot) {
  const payload = canonicalize({
    schemaVersion: snapshot.schemaVersion,
    connectorVersion: snapshot.connectorVersion,
    sourceSystem: snapshot.sourceSystem,
    sourceProject: snapshot.sourceProject,
    observationWindow: snapshot.observationWindow,
    importConfiguration: snapshot.importConfiguration,
    evidenceClass: snapshot.provenance?.evidenceClass,
    extraction: {
      complete: snapshot.extraction?.complete ?? null,
      truncatedReason: snapshot.extraction?.truncatedReason ?? null,
      changelogCapability: snapshot.extraction?.changelogCapability ?? null,
      worklogCapability: snapshot.extraction?.worklogCapability ?? null,
      slaCapability: snapshot.extraction?.slaCapability ?? null,
      searchCompleteness: snapshot.extraction?.searchCompleteness ?? null,
      changelogCompleteness: snapshot.extraction?.changelogCompleteness ?? null,
    },
    cases: snapshot.cases,
    events: snapshot.events,
    statuses: snapshot.statuses,
    requestTypes: snapshot.requestTypes,
    intervals: snapshot.intervals,
    dataQuality: (snapshot.dataQuality ?? []).map((item) => ({
      metricId: item.metricId,
      value: item.value,
      status: item.status,
      numerator: item.numerator,
      denominator: item.denominator,
    })),
  });
  return createHash("sha256").update(JSON.stringify(payload)).digest("hex");
}

export function stableId(parts) {
  return createHash("sha256").update(parts.join("\u0000")).digest("hex").slice(0, 24);
}

export function pseudonym(value, scope = "") {
  if (!value) return null;
  return `ref_${createHash("sha256").update(`${scope}\u0000${value}`).digest("hex").slice(0, 16)}`;
}
