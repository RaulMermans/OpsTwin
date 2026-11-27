import { observationWindow } from "./time.js";
import { buildSnapshot } from "./snapshot.js";

function mulberry32(seed) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

const GOLDEN_ISSUES = [
  {
    key: "OPS-GOLD-1",
    created: "2026-10-01T09:00:00.000Z",
    resolutiondate: "2026-10-02T09:00:00.000Z",
    updated: "2026-10-02T09:00:00.000Z",
    status: { id: "3", name: "Done", statusCategory: { key: "done" } },
    priority: { id: "2", name: "High" },
    requestTypeId: "rt-help",
    assigneeAccountId: "acct-a",
    changelog: [
      { id: "c1", field: "status", created: "2026-10-01T10:00:00.000Z", from: "1", to: "2", fromString: "Open", toString: "In Progress" },
      { id: "c2", field: "status", created: "2026-10-02T09:00:00.000Z", from: "2", to: "3", fromString: "In Progress", toString: "Done" },
      { id: "c3", field: "resolution", created: "2026-10-02T09:00:00.000Z", from: null, to: "10000" },
      { id: "c4", field: "assignee", created: "2026-10-01T10:00:00.000Z", from: null, to: "acct-a" },
    ],
    worklogs: [{ id: "w1", started: "2026-10-01T11:00:00.000Z", timeSpentSeconds: 3600 }],
    sla: [{ id: "s1", name: "Time to resolution", startTime: "2026-10-01T09:00:00.000Z", stopTime: "2026-10-02T09:00:00.000Z", elapsedMinutes: 1440, breached: false }],
    syntheticOrigin: true,
  },
  {
    key: "OPS-GOLD-2",
    created: "2026-10-03T12:00:00.000Z",
    resolutiondate: null,
    updated: "2026-10-03T12:00:00.000Z",
    status: { id: "1", name: "Open", statusCategory: { key: "new" } },
    priority: { id: "3", name: "Medium" },
    requestTypeId: "rt-hardware",
    assigneeAccountId: null,
    changelog: [],
    worklogs: [],
    sla: [],
    syntheticOrigin: true,
  },
  {
    key: "OPS-GOLD-3",
    created: "2026-09-20T08:00:00.000Z",
    resolutiondate: "2026-09-21T08:00:00.000Z",
    updated: "2026-10-04T08:00:00.000Z",
    status: { id: "1", name: "Open", statusCategory: { key: "new" } },
    priority: { id: "1", name: "Highest" },
    requestTypeId: "rt-access",
    assigneeAccountId: "acct-b",
    reopened: true,
    changelog: [
      { id: "c5", field: "status", created: "2026-09-21T08:00:00.000Z", from: "1", to: "3" },
      { id: "c6", field: "resolution", created: "2026-09-21T08:00:00.000Z", from: null, to: "10000" },
      { id: "c7", field: "resolution", created: "2026-10-04T08:00:00.000Z", from: "10000", to: null },
      { id: "c8", field: "status", created: "2026-10-04T08:00:00.000Z", from: "3", to: "1" },
      { id: "c9", field: "assignee", created: "2026-10-04T08:00:00.000Z", from: "acct-a", to: "acct-b" },
    ],
    worklogs: [],
    sla: [{ id: "s2", name: "Time to resolution", startTime: "2026-09-20T08:00:00.000Z", stopTime: "2026-09-21T08:00:00.000Z", elapsedMinutes: 1440, breached: true }],
    syntheticOrigin: true,
  },
];

const GOLDEN_STATUSES = [
  { id: "1", name: "Open", statusCategory: { key: "new" } },
  { id: "2", name: "In Progress", statusCategory: { key: "indeterminate" } },
  { id: "3", name: "Done", statusCategory: { key: "done" } },
];

const GOLDEN_TYPES = [
  { requestTypeId: "rt-help", name: "Get IT help" },
  { requestTypeId: "rt-hardware", name: "Request new hardware" },
  { requestTypeId: "rt-access", name: "Request admin access" },
];

function extractionComplete(overrides = {}) {
  return {
    complete: true,
    truncatedReason: null,
    pageCount: 1,
    retryCount: 0,
    inconsistentSource: false,
    authorized: true,
    worklogCapability: "retrieved",
    slaCapability: "retrieved",
    changelogCapability: "retrieved",
    ...overrides,
  };
}

function snapshotFromIssues(issues, profile, seed, now, extraExtraction = {}) {
  const window = observationWindow(30, now);
  window.windowDays = 30;
  return buildSnapshot({
    issues,
    statuses: GOLDEN_STATUSES.map((status) => ({
      statusId: status.id,
      displayName: status.name,
      sourceCategory: status.statusCategory.key,
      operationalClass: "unresolved",
      mappingStatus: "unresolved",
      classificationProvenance: "CG-2 does not map source statuses onto simulation stages.",
    })),
    requestTypes: GOLDEN_TYPES,
    sourceProject: { reference: "project:OPS", key: "OPS", name: "OpsTwin IT Support Lab", serviceDeskId: "1" },
    window,
    importConfiguration: {
      windowDays: 30,
      recordLimit: 1000,
      pageLimit: 10,
      cohortPolicy: "open-during-window",
      includeWorklogs: true,
      includeSla: true,
    },
    extraction: extractionComplete(extraExtraction),
    importStartedAt: now.toISOString(),
    importCompletedAt: now.toISOString(),
    authorizedInstallationRef: "offline-synthetic",
    evidenceClass: "synthetic",
    transportAuthenticity: "offline_fixture",
    sourceEndpoint: `synthetic:${profile}:${seed}`,
  });
}

export function goldenIssues() {
  return GOLDEN_ISSUES.map((issue) => structuredClone(issue));
}

export function generateSynthetic(profile = "golden", seed = 20261127, now = new Date("2026-10-15T00:00:00.000Z")) {
  if (profile === "golden") {
    return snapshotFromIssues(goldenIssues(), profile, seed, now);
  }
  const random = mulberry32(seed);
  const types = GOLDEN_TYPES;
  const issues = [];
  const count = profile === "medium" ? 400 : profile === "known-process" ? 200 : 80;
  for (let index = 0; index < count; index += 1) {
    const createdOffset = Math.floor(random() * 28) * 86400000 + Math.floor(random() * 24) * 3600000;
    const created = new Date(Date.parse("2026-09-20T00:00:00.000Z") + createdOffset).toISOString();
    const durationHours = 2 + Math.floor(random() * 72);
    const resolvedAt = new Date(Date.parse(created) + durationHours * 3600000).toISOString();
    const open = random() < 0.2;
    const missingHistory = profile === "stress" && random() < 0.3;
    const duplicate = profile === "stress" && index === 3;
    const invalid = profile === "stress" && index === 5;
    const type = types[Math.floor(random() * types.length)];
    const issue = {
      key: duplicate ? "OPS-SYN-1" : `OPS-SYN-${index + 1}`,
      created: invalid ? "not-a-date" : created,
      resolutiondate: open ? null : resolvedAt,
      updated: open ? created : resolvedAt,
      status: open ? GOLDEN_STATUSES[0] : GOLDEN_STATUSES[2],
      priority: { id: String(1 + Math.floor(random() * 3)), name: "generated" },
      requestTypeId: type.requestTypeId,
      assigneeAccountId: random() < 0.7 ? `acct-${Math.floor(random() * 5)}` : null,
      changelog: missingHistory
        ? []
        : [
            { id: `${index}-s1`, field: "status", created: new Date(Date.parse(created) + 3600000).toISOString(), from: "1", to: open ? "2" : "3" },
            ...(open ? [] : [{ id: `${index}-r1`, field: "resolution", created: resolvedAt, from: null, to: "10000" }]),
          ],
      worklogs: random() < 0.4 ? [{ id: `${index}-w`, started: created, timeSpentSeconds: 900 }] : [],
      sla: random() < 0.5 ? [{ id: `${index}-sla`, name: "Time to resolution", startTime: created, stopTime: open ? null : resolvedAt, elapsedMinutes: durationHours * 60, breached: random() < 0.15 }] : [],
      syntheticOrigin: true,
    };
    issues.push(issue);
  }
  if (profile === "stress") {
    issues.push({
      key: "OPS-SYN-BAD",
      created: "2026-10-01T00:00:00.000Z",
      resolutiondate: "2026-09-01T00:00:00.000Z",
      updated: "2026-10-01T00:00:00.000Z",
      status: GOLDEN_STATUSES[2],
      priority: { id: "2", name: "High" },
      requestTypeId: null,
      changelog: [{ id: "lead", field: "status", created: "2026-09-01T00:00:00.000Z", from: "1", to: "3" }],
      worklogs: [],
      sla: [],
      syntheticOrigin: true,
    });
  }
  return snapshotFromIssues(issues, profile, seed, now, profile === "stress" ? { inconsistentSource: true } : {});
}

export const SYNTHETIC_PROFILES = ["golden", "medium", "stress", "known-process"];
