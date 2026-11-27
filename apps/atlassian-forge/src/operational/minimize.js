const CASE_KEYS = [
  "caseId",
  "sourceReference",
  "projectReference",
  "requestTypeReference",
  "priorityReference",
  "currentStatusReference",
  "createdAt",
  "resolvedAt",
  "createdAtInvalid",
  "observationStatus",
  "syntheticOrigin",
  "originUnknown",
  "reopened",
];

const EVENT_KEYS = [
  "eventId",
  "caseId",
  "eventType",
  "occurredAt",
  "observedAt",
  "previousValue",
  "newValue",
  "sourceReference",
  "durationMinutes",
  "provenance",
];

function pick(item, keys) {
  const out = {};
  for (const key of keys) {
    if (item && item[key] !== undefined) out[key] = item[key];
  }
  return out;
}

export function minimizeSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") return null;
  return {
    schemaVersion: snapshot.schemaVersion,
    snapshotId: snapshot.snapshotId,
    connectorVersion: snapshot.connectorVersion,
    sourceSystem: snapshot.sourceSystem,
    sourceProject: snapshot.sourceProject,
    authorizedInstallationRef: snapshot.authorizedInstallationRef ?? null,
    observationWindow: snapshot.observationWindow,
    importTimestamp: snapshot.importTimestamp,
    importStartedAt: snapshot.importStartedAt,
    importCompletedAt: snapshot.importCompletedAt,
    importConfiguration: snapshot.importConfiguration,
    cases: (snapshot.cases ?? []).map((item) => pick(item, CASE_KEYS)),
    events: (snapshot.events ?? []).map((item) => pick(item, EVENT_KEYS)),
    statuses: snapshot.statuses ?? [],
    requestTypes: snapshot.requestTypes ?? [],
    intervals: snapshot.intervals ?? [],
    descriptiveEvidence: snapshot.descriptiveEvidence ?? [],
    dataQuality: snapshot.dataQuality ?? [],
    completenessStatus: snapshot.completenessStatus,
    readiness: snapshot.readiness,
    provenance: snapshot.provenance,
    contentFingerprint: snapshot.contentFingerprint,
    limitations: snapshot.limitations ?? [],
    extraction: snapshot.extraction,
  };
}
