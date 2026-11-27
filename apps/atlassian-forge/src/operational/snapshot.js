import { contentFingerprint, stableId } from "./fingerprint.js";
import { CONNECTOR_VERSION, SCHEMA_VERSION, provenance } from "./provenance.js";
import { normalizeIssues } from "./normalize.js";
import { assessDataQuality, classifyReadiness, descriptiveEvidence } from "./quality.js";
import { validateSnapshot } from "./validate.js";

export function dedupeSourceIssues(issues) {
  const seen = new Set();
  const out = [];
  for (const issue of issues) {
    const key = String(issue.key ?? issue.sourceReference ?? "");
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(issue);
  }
  return out;
}

export function buildSnapshot({
  issues,
  statuses = [],
  requestTypes = [],
  sourceProject,
  window,
  importConfiguration,
  extraction,
  importStartedAt,
  importCompletedAt,
  authorizedInstallationRef = null,
  sourceSystem = "jira-jsm",
  evidenceClass = "observed",
  transportAuthenticity = "live_api",
  sourceEndpoint = "search-jql",
}) {
  const uniqueIssues = dedupeSourceIssues(issues);
  const meta = {
    sourceSystem,
    projectReference: sourceProject.reference,
    sourceEndpoint,
    evidenceClass,
    transportAuthenticity,
    observationWindowLabel: `${window.start}/${window.end}`,
    observedAt: importCompletedAt ?? importStartedAt ?? null,
    installationRef: authorizedInstallationRef,
  };
  const normalized = normalizeIssues(uniqueIssues, meta, window, statuses, requestTypes);
  const dataQuality = assessDataQuality(normalized, extraction, window);
  const readiness = classifyReadiness(dataQuality, extraction, normalized.cases.length);
  const provenanceRoot = provenance({
    sourceSystem,
    sourceProject: sourceProject.reference,
    sourceEndpoint,
    extractionTimestamp: importCompletedAt ?? null,
    sourceRecordReference: sourceProject.reference,
    evidenceClass,
    observationWindow: `${window.start}/${window.end}`,
    derivationMethod: "bounded-import-os.1.0.0",
    transportAuthenticity,
  });
  const descriptive = descriptiveEvidence(normalized, window, provenanceRoot);
  const limitations = [
    "This snapshot is observational evidence, not a calibrated simulation model.",
    "Status residence time is not active processing time.",
    "Recorded work duration is not utilization.",
    "Live transport does not change synthetic data origin.",
    extraction.complete ? null : "Extraction was incomplete; completeness is partial.",
    extraction.inconsistentSource ? "Source records may have changed during import." : null,
  ].filter(Boolean);

  const snapshot = {
    schemaVersion: SCHEMA_VERSION,
    snapshotId: `snap_${stableId([importStartedAt ?? "t", sourceProject.reference, window.start, window.end])}`,
    connectorVersion: CONNECTOR_VERSION,
    sourceSystem,
    sourceProject,
    authorizedInstallationRef,
    observationWindow: { start: window.start, end: window.end, convention: window.convention },
    importTimestamp: importCompletedAt ?? importStartedAt,
    importStartedAt: importStartedAt ?? null,
    importCompletedAt: importCompletedAt ?? null,
    importConfiguration,
    cases: normalized.cases,
    events: normalized.events,
    statuses: normalized.statuses,
    requestTypes: normalized.requestTypes,
    intervals: normalized.intervals,
    descriptiveEvidence: descriptive,
    dataQuality,
    completenessStatus: readiness.completenessStatus,
    readiness: readiness.readiness,
    provenance: provenanceRoot,
    contentFingerprint: "0".repeat(64),
    limitations,
    extraction: {
      complete: extraction.complete,
      truncatedReason: extraction.truncatedReason ?? null,
      pageCount: extraction.pageCount ?? 0,
      retryCount: extraction.retryCount ?? 0,
      inconsistentSource: Boolean(extraction.inconsistentSource),
      worklogCapability: extraction.worklogCapability ?? "not_requested",
      slaCapability: extraction.slaCapability ?? "not_requested",
      changelogCapability: extraction.changelogCapability ?? "retrieved",
      searchCompleteness: extraction.searchCompleteness ?? null,
      changelogCompleteness: extraction.changelogCompleteness ?? null,
      requestTypeCompleteness: extraction.requestTypeCompleteness ?? null,
      worklogCompleteness: extraction.worklogCompleteness ?? null,
      slaCompleteness: extraction.slaCompleteness ?? null,
    },
  };
  snapshot.contentFingerprint = contentFingerprint(snapshot);
  const contract = validateSnapshot(snapshot);
  if (!contract.ok) {
    snapshot.completenessStatus = "invalid";
    snapshot.readiness = "invalid";
    snapshot.limitations = [...snapshot.limitations, `Snapshot failed the os.1.0.0 contract at ${contract.path}: ${contract.message}`];
    snapshot.contentFingerprint = contentFingerprint(snapshot);
  }
  return snapshot;
}
