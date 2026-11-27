import { stableId, pseudonym } from "./fingerprint.js";
import { provenance, SCHEMA_VERSION } from "./provenance.js";
import { durationMinutes, parseTimestamp } from "./time.js";

const EVENT_ORDER = [
  "case_created",
  "status_changed",
  "assigned",
  "reassigned",
  "priority_changed",
  "resolved",
  "reopened",
  "worklog_recorded",
  "sla_cycle_observed",
];

export function statusRecord(status) {
  const statusId = String(status.id ?? status.statusId);
  return {
    statusId,
    displayName: String(status.name ?? status.displayName ?? statusId),
    sourceCategory: status.statusCategory?.key ?? status.sourceCategory ?? null,
    operationalClass: "unresolved",
    mappingStatus: "unresolved",
    classificationProvenance: "CG-2 does not map source statuses onto simulation stages.",
  };
}

export function compareEvents(a, b) {
  const aMs = parseTimestamp(a.occurredAt).utcMs ?? Number.POSITIVE_INFINITY;
  const bMs = parseTimestamp(b.occurredAt).utcMs ?? Number.POSITIVE_INFINITY;
  if (aMs !== bMs) return aMs - bMs;
  const typeDelta = EVENT_ORDER.indexOf(a.eventType) - EVENT_ORDER.indexOf(b.eventType);
  if (typeDelta !== 0) return typeDelta;
  return a.eventId.localeCompare(b.eventId);
}

export function dedupeEvents(events) {
  const seen = new Set();
  const out = [];
  for (const event of [...events].sort(compareEvents)) {
    const key = [event.caseId, event.eventType, event.occurredAt, event.previousValue, event.newValue, event.sourceReference].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(event);
  }
  return out;
}

function baseProvenance(meta, recordRef, evidenceClass, extra = {}) {
  return provenance({
    sourceSystem: meta.sourceSystem,
    sourceProject: meta.projectReference,
    sourceEndpoint: extra.sourceEndpoint ?? meta.sourceEndpoint ?? null,
    extractionTimestamp: extra.extractionTimestamp ?? null,
    sourceRecordReference: recordRef,
    evidenceClass,
    observationWindow: meta.observationWindowLabel ?? null,
    derivationMethod: extra.derivationMethod ?? null,
    transportAuthenticity: meta.transportAuthenticity,
  });
}

export function normalizeCase(issue, meta) {
  const created = parseTimestamp(issue.created);
  const resolved = parseTimestamp(issue.resolutiondate ?? issue.resolvedAt ?? null);
  const statusId = issue.status?.id ? String(issue.status.id) : issue.currentStatusReference ?? null;
  const requestTypeId = issue.requestTypeId ?? issue.requestType?.id ?? null;
  const priorityId = issue.priority?.id ? String(issue.priority.id) : issue.priorityReference ?? null;
  const sourceRef = String(issue.key ?? issue.sourceReference);
  const caseId = stableId(["case", meta.sourceSystem, meta.projectReference, sourceRef]);
  let observationStatus = "unknown";
  if (issue.reopened) observationStatus = "reopened";
  else if (resolved.ok) observationStatus = "resolved";
  else if (created.ok && !issue.resolutiondate && issue.resolutiondate !== undefined) observationStatus = "open";
  else if (created.ok && !resolved.ok && (issue.resolutiondate === null || issue.resolutiondate === undefined)) {
    observationStatus = "open";
  }
  return {
    schemaVersion: SCHEMA_VERSION,
    caseId,
    sourceReference: sourceRef,
    sourceSystem: meta.sourceSystem,
    projectReference: meta.projectReference,
    requestTypeReference: requestTypeId ? String(requestTypeId) : null,
    priorityReference: priorityId,
    createdAt: created.ok ? created.utcIso : null,
    resolvedAt: resolved.ok ? resolved.utcIso : null,
    currentStatusReference: statusId,
    observationStatus,
    lifecycleCompleteness: "unknown",
    assigneeReference: issue.assigneeAccountId ? pseudonym(issue.assigneeAccountId) : null,
    updatedAt: parseTimestamp(issue.updated).ok ? parseTimestamp(issue.updated).utcIso : null,
    createdAtInvalid: Boolean(issue.created) && !created.ok,
    syntheticOrigin: Boolean(issue.syntheticOrigin || meta.evidenceClass === "synthetic"),
    provenance: baseProvenance(meta, sourceRef, issue.syntheticOrigin ? "synthetic" : meta.evidenceClass),
  };
}

export function eventFromParts(caseId, type, occurredAt, previousValue, newValue, sourceReference, meta, extra = {}) {
  const occurred = parseTimestamp(occurredAt);
  return {
    eventId: stableId(["event", caseId, type, occurred.utcIso ?? "invalid", previousValue ?? "", newValue ?? "", sourceReference]),
    caseId,
    eventType: type,
    occurredAt: occurred.ok ? occurred.utcIso : null,
    observedAt: meta.observedAt ?? null,
    previousValue: previousValue ?? null,
    newValue: newValue ?? null,
    sourceReference,
    durationMinutes: extra.durationMinutes ?? null,
    provenance: baseProvenance(meta, sourceReference, extra.evidenceClass ?? meta.evidenceClass, extra),
  };
}

export function eventsFromIssue(issue, caseRecord, meta) {
  const events = [];
  const createdSource = `${caseRecord.sourceReference}:created`;
  events.push(eventFromParts(caseRecord.caseId, "case_created", issue.created, null, caseRecord.currentStatusReference, createdSource, meta));
  for (const item of issue.changelog ?? []) {
    const field = item.field;
    const created = item.created;
    const from =
      item.from !== undefined && item.from !== null
        ? String(item.from)
        : typeof item.fromString === "string"
          ? item.fromString
          : null;
    const to =
      item.to !== undefined && item.to !== null
        ? String(item.to)
        : typeof item.toString === "string"
          ? item.toString
          : null;
    const source = `${caseRecord.sourceReference}:changelog:${item.id ?? `${field}:${created}`}`;
    if (field === "status") {
      events.push(eventFromParts(caseRecord.caseId, "status_changed", created, item.from ?? from, item.to ?? to, source, meta));
    } else if (field === "assignee") {
      const type = from ? "reassigned" : "assigned";
      events.push(
        eventFromParts(
          caseRecord.caseId,
          type,
          created,
          from ? pseudonym(from) : null,
          to ? pseudonym(to) : null,
          source,
          meta,
        ),
      );
    } else if (field === "priority") {
      events.push(eventFromParts(caseRecord.caseId, "priority_changed", created, from, to, source, meta));
    } else if (field === "resolution") {
      if (to && !from) {
        events.push(eventFromParts(caseRecord.caseId, "resolved", created, from, to, source, meta));
      } else if (from && !to) {
        events.push(eventFromParts(caseRecord.caseId, "reopened", created, from, to, source, meta));
      }
    }
  }
  for (const worklog of issue.worklogs ?? []) {
    const seconds = Number(worklog.timeSpentSeconds);
    const minutes = Number.isFinite(seconds) && seconds >= 0 ? seconds / 60 : null;
    events.push(
      eventFromParts(
        caseRecord.caseId,
        "worklog_recorded",
        worklog.started ?? worklog.created,
        null,
        String(worklog.id ?? "worklog"),
        `${caseRecord.sourceReference}:worklog:${worklog.id ?? "unknown"}`,
        meta,
        { durationMinutes: minutes, sourceEndpoint: "issue-worklog" },
      ),
    );
  }
  for (const sla of issue.sla ?? []) {
    events.push(
      eventFromParts(
        caseRecord.caseId,
        "sla_cycle_observed",
        sla.stopTime ?? sla.startTime ?? issue.created,
        sla.breached ? "breached" : "not_breached",
        sla.name ?? sla.id ?? "sla",
        `${caseRecord.sourceReference}:sla:${sla.id ?? sla.name ?? "unknown"}`,
        meta,
        { durationMinutes: sla.elapsedMinutes ?? null, sourceEndpoint: "request-sla" },
      ),
    );
  }
  return events;
}

function applyObservationStatus(caseRecord, events) {
  const resolvedEvents = events.filter((event) => event.eventType === "resolved").sort(compareEvents);
  const reopenedEvents = events.filter((event) => event.eventType === "reopened").sort(compareEvents);
  if (reopenedEvents.length > 0) {
    const lastReopen = reopenedEvents[reopenedEvents.length - 1];
    const lastResolve = resolvedEvents[resolvedEvents.length - 1];
    const reopenMs = parseTimestamp(lastReopen.occurredAt).utcMs ?? 0;
    const resolveMs = parseTimestamp(lastResolve?.occurredAt).utcMs ?? 0;
    if (reopenMs >= resolveMs) return { ...caseRecord, observationStatus: "reopened", resolvedAt: caseRecord.resolvedAt };
    return { ...caseRecord, observationStatus: "resolved" };
  }
  if (resolvedEvents.length > 0 || caseRecord.resolvedAt) {
    return { ...caseRecord, observationStatus: "resolved" };
  }
  if (caseRecord.createdAt) return { ...caseRecord, observationStatus: "open" };
  return { ...caseRecord, observationStatus: "unknown" };
}

export function reconstructLifecycle(caseRecord, events, window) {
  const related = events.filter((event) => event.caseId === caseRecord.caseId).sort(compareEvents);
  const intervals = [];
  const statusEvents = related.filter((event) => event.eventType === "status_changed" && event.occurredAt);
  const created = related.find((event) => event.eventType === "case_created");
  let completeness = "unknown";
  let cursorStatus = null;
  let cursorStart = caseRecord.createdAt;
  if (statusEvents.length === 0) {
    if (caseRecord.currentStatusReference && caseRecord.createdAt) {
      cursorStatus = caseRecord.currentStatusReference;
      completeness = "incomplete";
    }
  } else {
    const first = statusEvents[0];
    if (first.previousValue) {
      cursorStatus = first.previousValue;
      completeness = created?.occurredAt && first.occurredAt ? "complete" : "incomplete";
    } else {
      completeness = "incomplete";
      cursorStatus = first.newValue;
      cursorStart = first.occurredAt;
    }
  }

  const points = [];
  if (cursorStatus && cursorStart) points.push({ at: cursorStart, status: cursorStatus, syntheticStart: true });
  for (const event of statusEvents) {
    points.push({ at: event.occurredAt, status: event.newValue, previous: event.previousValue });
  }

  for (let index = 0; index < points.length; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    const endAt = end ? end.at : caseRecord.resolvedAt && caseRecord.observationStatus === "resolved" ? caseRecord.resolvedAt : window.end;
    const openEnded = !end && caseRecord.observationStatus !== "resolved";
    const duration = start.at && endAt ? durationMinutes(start.at, endAt) : { ok: false, minutes: null, reason: "invalid" };
    const left = window.start && start.at && Date.parse(start.at) < Date.parse(window.start);
    const right = openEnded || (endAt && Date.parse(endAt) >= Date.parse(window.end));
    let censoring = "none";
    if (!duration.ok && duration.reason === "negative") {
      intervals.push({
        intervalId: stableId(["interval", caseRecord.caseId, "invalid", start.at ?? "x", String(index)]),
        caseId: caseRecord.caseId,
        intervalType: "unknown",
        startAt: start.at,
        endAt,
        durationMinutes: null,
        censoring: "unknown",
        complete: false,
        statusReference: start.status,
      });
      continue;
    }
    if (left && right) censoring = "both";
    else if (left) censoring = "left";
    else if (right) censoring = "right";
    intervals.push({
      intervalId: stableId(["interval", caseRecord.caseId, "status", start.at ?? "x", String(index)]),
      caseId: caseRecord.caseId,
      intervalType: "status_residence",
      startAt: start.at,
      endAt: openEnded ? window.end : endAt,
      durationMinutes: duration.ok ? duration.minutes : null,
      censoring,
      complete: duration.ok && !openEnded && !left && !right,
      statusReference: start.status,
    });
  }

  if (!caseRecord.createdAt) {
    completeness = "unknown";
    intervals.push({
      intervalId: stableId(["interval", caseRecord.caseId, "unknown-start"]),
      caseId: caseRecord.caseId,
      intervalType: "unknown",
      startAt: null,
      endAt: null,
      durationMinutes: null,
      censoring: "unknown",
      complete: false,
      statusReference: caseRecord.currentStatusReference,
    });
  } else {
    const lifetimeEnd =
      caseRecord.resolvedAt && caseRecord.observationStatus === "resolved" ? caseRecord.resolvedAt : window.end;
    const lifetime = durationMinutes(caseRecord.createdAt, lifetimeEnd);
    const left = Date.parse(caseRecord.createdAt) < Date.parse(window.start);
    const open = caseRecord.observationStatus !== "resolved";
    let censoring = "none";
    if (left && open) censoring = "both";
    else if (left) censoring = "left";
    else if (open) censoring = "right";
    intervals.push({
      intervalId: stableId(["interval", caseRecord.caseId, "lifetime"]),
      caseId: caseRecord.caseId,
      intervalType: "elapsed_lifetime",
      startAt: caseRecord.createdAt,
      endAt: lifetimeEnd,
      durationMinutes: lifetime.ok ? lifetime.minutes : null,
      censoring,
      complete: lifetime.ok && !open && !left,
      statusReference: null,
    });
  }

  for (const event of related.filter((item) => item.eventType === "worklog_recorded")) {
    intervals.push({
      intervalId: stableId(["interval", caseRecord.caseId, "work", event.eventId]),
      caseId: caseRecord.caseId,
      intervalType: "recorded_work",
      startAt: event.occurredAt,
      endAt: event.occurredAt,
      durationMinutes: event.durationMinutes,
      censoring: event.durationMinutes === null ? "unknown" : "none",
      complete: event.durationMinutes !== null,
      statusReference: null,
    });
  }

  for (const event of related.filter((item) => item.eventType === "sla_cycle_observed")) {
    intervals.push({
      intervalId: stableId(["interval", caseRecord.caseId, "sla", event.eventId]),
      caseId: caseRecord.caseId,
      intervalType: "sla_elapsed",
      startAt: event.occurredAt,
      endAt: event.occurredAt,
      durationMinutes: event.durationMinutes,
      censoring: event.durationMinutes === null ? "unknown" : "none",
      complete: event.durationMinutes !== null,
      statusReference: null,
    });
  }

  const createdMs = parseTimestamp(caseRecord.createdAt).utcMs;
  const leading = related.some((event) => {
    const ms = parseTimestamp(event.occurredAt).utcMs;
    return createdMs !== null && ms !== null && ms < createdMs && event.eventType !== "case_created";
  });
  if (leading) completeness = completeness === "complete" ? "incomplete" : completeness;

  return {
    caseRecord: { ...caseRecord, lifecycleCompleteness: completeness },
    intervals,
  };
}

export function normalizeIssues(issues, meta, window, statusCatalog = [], requestTypes = []) {
  const statuses = new Map(statusCatalog.map((status) => [status.statusId, status]));
  const cases = [];
  let events = [];
  let intervals = [];
  for (const issue of issues) {
    let caseRecord = normalizeCase(issue, meta);
    const issueEvents = eventsFromIssue(issue, caseRecord, meta);
    caseRecord = applyObservationStatus(caseRecord, issueEvents);
    const lifecycle = reconstructLifecycle(caseRecord, issueEvents, window);
    cases.push(lifecycle.caseRecord);
    events.push(...issueEvents);
    intervals.push(...lifecycle.intervals);
    if (issue.status) {
      const record = statusRecord(issue.status);
      if (!statuses.has(record.statusId)) statuses.set(record.statusId, record);
    }
  }
  events = dedupeEvents(events);
  cases.sort((a, b) => a.caseId.localeCompare(b.caseId));
  intervals.sort((a, b) => a.intervalId.localeCompare(b.intervalId));
  return {
    cases,
    events,
    intervals,
    statuses: [...statuses.values()].sort((a, b) => a.statusId.localeCompare(b.statusId)),
    requestTypes: [...requestTypes].sort((a, b) => a.requestTypeId.localeCompare(b.requestTypeId)),
  };
}
