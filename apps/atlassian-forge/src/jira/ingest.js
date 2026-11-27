import { classifyJiraResponse, classifyNetworkFailure } from "./classify-response.js";
import { fetchWithRetry } from "./http.js";
import { paginateOffset, paginateToken } from "./paginate.js";
import { cohortJql, observationWindow, overlapsObservationWindow } from "../operational/time.js";
import { statusRecord } from "../operational/normalize.js";
import { buildSnapshot } from "../operational/snapshot.js";
import { validateSnapshot } from "../operational/validate.js";

export const IMPORT_LIMITS = {
  recordLimit: 40,
  pageLimit: 8,
  pageSize: 20,
  changelogPageSize: 100,
  enrichLimit: 40,
  deadlineMs: 20000,
  stageCallLimits: {
    search: 10,
    changelog: 120,
    worklog: 45,
    sla: 45,
    metadata: 20,
  },
};

const SEARCH_FIELDS = "created,resolutiondate,status,priority,issuetype,assignee,project,updated,labels";

function failed(classification, message, extra = {}) {
  return { status: "failed", classification, message, ...extra };
}

export function parseWindowDays(payload) {
  const windowDays = payload?.windowDays ?? 30;
  if (![30, 60, 90].includes(windowDays)) {
    return { error: "Observation window must be 30, 60, or 90 days." };
  }
  return { windowDays };
}

function changelogItems(histories) {
  const items = [];
  for (const history of histories ?? []) {
    for (const item of history.items ?? []) {
      if (!["status", "assignee", "priority", "resolution"].includes(item.field)) continue;
      items.push({
        id: `${history.id}:${item.field}:${item.to ?? ""}`,
        field: item.field,
        created: history.created,
        from: item.from ?? null,
        to: item.to ?? null,
        fromString: item.fromString ?? null,
        toString: item.toString ?? null,
      });
    }
  }
  return items;
}

function requestTypeFromFields(fields, requestTypeFieldId) {
  if (requestTypeFieldId && fields?.[requestTypeFieldId]) {
    const value = fields[requestTypeFieldId];
    if (value?.requestType?.id) return String(value.requestType.id);
    if (value?.id) return String(value.id);
  }
  return null;
}

function findRequestTypeField(fields) {
  for (const field of fields ?? []) {
    const custom = field?.schema?.custom;
    if (typeof custom === "string" && custom.includes("servicedesk") && custom.includes("request")) {
      return field.id;
    }
    if (field?.name === "Request Type") return field.id;
  }
  return null;
}

function slaCycles(item) {
  const completed = Array.isArray(item.completedCycles) ? item.completedCycles : [];
  const cycles = completed.map((cycle) => ({ ...cycle, ongoing: false }));
  if (item.ongoingCycle) cycles.push({ ...item.ongoingCycle, ongoing: true });
  return cycles.map((cycle, index) => {
    const elapsedMs = Number(cycle?.elapsedTime?.millis);
    const breached = cycle?.breached;
    return {
      id: `${item.id}:${index}`,
      name: item.name,
      startTime: cycle?.startTime?.iso8601 ?? cycle?.startTime ?? null,
      stopTime: cycle?.stopTime?.iso8601 ?? cycle?.stopTime ?? null,
      elapsedMinutes: Number.isFinite(elapsedMs) ? elapsedMs / 60000 : null,
      breached: breached === true ? true : breached === false ? false : null,
      ongoing: Boolean(cycle.ongoing),
    };
  });
}

export function issueToRecord(issue, projectKey, requestTypeFieldId) {
  const fields = issue.fields ?? {};
  const labelsPresent = Array.isArray(fields.labels);
  return {
    key: issue.key,
    id: issue.id,
    created: fields.created,
    resolutiondate: fields.resolutiondate ?? null,
    updated: fields.updated,
    status: fields.status ?? null,
    priority: fields.priority ?? null,
    requestTypeId: requestTypeFromFields(fields, requestTypeFieldId),
    assigneeAccountId: fields.assignee?.accountId ?? null,
    project: fields.project ?? { key: projectKey },
    changelog: changelogItems(issue.changelog?.histories),
    changelogComplete: false,
    worklogs: [],
    sla: [],
    syntheticOrigin: labelsPresent && fields.labels.includes("opstwin-synthetic"),
    originUnknown: !labelsPresent,
  };
}

function withLastPage(body) {
  if (!body || typeof body !== "object") return { values: [], isLastPage: true };
  if (body.isLast === true || body.isLastPage === true) return body;
  if (Number.isFinite(body.total)) return body;
  return { ...body, isLastPage: true };
}

function completenessOf(result, optional = false) {
  if (!result) return optional ? "unavailable" : "incomplete";
  if (result === "forbidden") return "forbidden";
  if (result === "unavailable") return "unavailable";
  if (result === "not_requested") return "not_requested";
  if (result.complete) return result.items?.length === 0 ? "empty" : "complete";
  return "incomplete";
}

export async function ingestOperationalData({
  projectKey,
  installationRef,
  payload,
  now,
  requestJson,
  clock = { nowMs: () => Date.now() },
  limits = IMPORT_LIMITS,
  retrySleep,
}) {
  const parsed = parseWindowDays(payload);
  if (parsed.error) return failed("invalid_configuration", parsed.error);
  const window = observationWindow(parsed.windowDays, now);
  window.windowDays = parsed.windowDays;
  const startedMs = clock.nowMs();
  const importStartedAt = new Date(startedMs).toISOString();
  const stages = [];
  const telemetry = [];
  const stageDurations = {};
  let retryCount = 0;
  let pageCount = 0;
  let apiCalls = 0;
  const stageCalls = {};
  let truncatedReason = null;

  function remainingMs() {
    return limits.deadlineMs - (clock.nowMs() - startedMs);
  }

  function markStage(name) {
    const started = clock.nowMs();
    stages.push(name);
    return () => {
      stageDurations[name] = (stageDurations[name] ?? 0) + (clock.nowMs() - started);
    };
  }

  function budgetStop(stage) {
    stageCalls[stage] = (stageCalls[stage] ?? 0) + 1;
    if (remainingMs() <= 0) {
      truncatedReason = truncatedReason ?? "deadline";
      return "deadline";
    }
    if (stageCalls[stage] > (limits.stageCallLimits[stage] ?? Number.POSITIVE_INFINITY)) {
      truncatedReason = truncatedReason ?? "stage_budget";
      return "stage_budget";
    }
    return null;
  }

  async function call(path, schema, method = "GET", body, stage = "metadata") {
    const stop = budgetStop(stage);
    if (stop) return { error: failed(stop, "Import stopped before the request because the execution budget was exhausted.") };
    apiCalls += 1;
    const result = await fetchWithRetry(
      async () => {
        try {
          return await requestJson(path, method, body);
        } catch (error) {
          const classified = classifyNetworkFailure(error);
          return { status: 0, body: null, networkError: true, classification: classified };
        }
      },
      { remainingMs, ...(retrySleep ? { sleep: retrySleep } : {}) },
    );
    retryCount += result.retries ?? 0;
    if (result.stopped === "deadline") {
      truncatedReason = truncatedReason ?? "deadline";
      return { error: failed("deadline", "Import stopped because the execution budget was exhausted.") };
    }
    if (result.stopped === "retry_exceeds_deadline") {
      truncatedReason = truncatedReason ?? "retry_exceeds_deadline";
      return { error: failed("retry_exceeds_deadline", "Retry-After exceeds the remaining import deadline.") };
    }
    if (result.networkError) {
      return { error: failed(result.classification?.kind ?? "network_failure", result.classification?.message ?? "Network failure.") };
    }
    if (result.stopped === "authorization") {
      const classified = classifyJiraResponse(result.status, result.body, schema);
      return { error: failed(classified.kind, classified.message) };
    }
    if (result.stopped === "retry_exhausted") {
      return { error: failed("rate_limited", "Retry budget exhausted after rate limiting or upstream failure.") };
    }
    const classified = classifyJiraResponse(result.status, result.body, schema);
    if (classified.kind !== "ok" && classified.kind !== "empty") {
      return { error: failed(classified.kind, classified.message, { httpStatus: result.status }) };
    }
    return { body: result.body, classified };
  }

  const endValidate = markStage("validate_project");
  telemetry.push({ event: "import.started", projectKey });
  const project = await call(`/rest/api/3/project/${projectKey}`, "project");
  endValidate();
  if (project.error) return project.error;
  const sourceProject = {
    reference: `project:${project.body.key}`,
    key: project.body.key,
    name: project.body.name,
    serviceDeskId: null,
  };

  // shortcut: skip /myself (needs extra user scope); pad UTC in JQL and clip in normalization
  const timeZone = null;

  const endDesks = markStage("service_desk");
  const desksPaged = await paginateOffset({
    maxPages: limits.pageLimit,
    maxRecords: 80,
    pageSize: 50,
    identity: (item) => String(item.id),
    getItems: (page) => page.values ?? [],
    fetchPage: async (start, limit) => {
      const result = await call(`/rest/servicedeskapi/servicedesk?start=${start}&limit=${limit}`, "servicedesk-collection");
      if (result.error) return { error: result.error.classification, values: [] };
      return withLastPage(result.body);
    },
  });
  endDesks();
  pageCount += desksPaged.pages;
  const desk = desksPaged.items.find((item) => item.projectKey === projectKey) ?? null;
  if (!desksPaged.complete && !desk) truncatedReason = truncatedReason ?? desksPaged.reason ?? "incomplete_servicedesk";
  sourceProject.serviceDeskId = desk?.id !== undefined && desk?.id !== null ? String(desk.id) : null;

  let requestTypes = [];
  let requestTypeCompleteness = desk ? "incomplete" : "unavailable";
  if (desk) {
    const endTypes = markStage("request_types");
    const pagedTypes = await paginateOffset({
      maxPages: limits.pageLimit,
      maxRecords: 100,
      pageSize: 50,
      identity: (item) => String(item.id),
      getItems: (page) => page.values ?? [],
      fetchPage: async (start, limit) => {
        const result = await call(
          `/rest/servicedeskapi/servicedesk/${desk.id}/requesttype?start=${start}&limit=${limit}`,
          "request-type-collection",
        );
        if (result.error) return { error: result.error.classification, total: 0, values: [] };
        return result.body;
      },
    });
    endTypes();
    pageCount += pagedTypes.pages;
    requestTypes = pagedTypes.items.map((item) => ({ requestTypeId: String(item.id), name: String(item.name) }));
    requestTypeCompleteness = completenessOf(pagedTypes, true);
  }

  const endFields = markStage("fields");
  const fields = await call("/rest/api/3/field", "field-metadata");
  endFields();
  const requestTypeFieldId = fields.error ? null : findRequestTypeField(fields.body);

  const endStatuses = markStage("statuses");
  const statusBody = await call(`/rest/api/3/project/${projectKey}/statuses`, "project-statuses");
  endStatuses();
  const statuses = [];
  if (!statusBody.error && Array.isArray(statusBody.body)) {
    for (const type of statusBody.body) {
      for (const status of type.statuses ?? []) statuses.push(statusRecord(status));
    }
  }

  const endSearch = markStage("search");
  const jql = cohortJql(projectKey, window, timeZone);
  const search = await paginateToken({
    maxPages: limits.pageLimit,
    maxRecords: limits.recordLimit,
    identity: (issue) => issue.id ?? issue.key,
    getItems: (page) => page.issues ?? [],
    getToken: (page) => page.nextPageToken ?? null,
    fetchPage: async (token) => {
      const result = await call(
        "/rest/api/3/search/jql",
        "issue-search",
        "POST",
        {
          jql,
          maxResults: limits.pageSize,
          fields: `${SEARCH_FIELDS}${requestTypeFieldId ? `,${requestTypeFieldId}` : ""}`.split(","),
          expand: "changelog",
          ...(token ? { nextPageToken: token } : {}),
        },
        "search",
      );
      if (result.error) return { error: result.error.classification, issues: [] };
      return result.body;
    },
  });
  endSearch();
  pageCount += search.pages;
  if (search.reason && search.reason !== "record_budget" && search.reason !== "page_budget" && search.items.length === 0 && !search.complete) {
    return failed(search.reason, "Issue search could not be completed.");
  }

  const records = [];
  let rejectedCrossProject = 0;
  for (const issue of search.items) {
    if ((issue.fields?.project?.key ?? issue.key?.split("-")[0]) !== projectKey) {
      telemetry.push({ event: "import.rejected", reason: "cross_project_record" });
      rejectedCrossProject += 1;
      continue;
    }
    if (!overlapsObservationWindow(issue.fields?.created, issue.fields?.resolutiondate, window)) continue;
    records.push(issueToRecord(issue, projectKey, requestTypeFieldId));
  }
  if (rejectedCrossProject > 0) {
    truncatedReason = truncatedReason ?? "cross_project_rejected";
    return failed("cross_project_rejected", "Search returned records outside the authorized project. The import was not marked complete.");
  }

  const endChangelogs = markStage("changelogs");
  let changelogCapability = "retrieved";
  let changelogCompleteness = "complete";
  for (const record of records) {
    const paged = await paginateOffset({
      maxPages: 3,
      maxRecords: 200,
      pageSize: limits.changelogPageSize,
      identity: (item) => String(item.id),
      getItems: (page) => page.values ?? page.histories ?? [],
      getSourceCount: (page) => (page.values ?? page.histories ?? []).length,
      fetchPage: async (startAt, maxResults) => {
        const result = await call(
          `/rest/api/3/issue/${record.key}/changelog?startAt=${startAt}&maxResults=${maxResults}`,
          "changelog-collection",
          "GET",
          undefined,
          "changelog",
        );
        if (result.error) return { error: result.error.classification, values: [] };
        return result.body;
      },
    });
    pageCount += paged.pages;
    if (paged.reason === "permission_denied" || paged.reason === "authentication_failed") {
      changelogCapability = "forbidden";
      changelogCompleteness = "forbidden";
      record.changelogComplete = false;
      break;
    }
    if (paged.reason === "deadline" || paged.reason === "retry_exceeds_deadline" || paged.reason === "stage_budget") {
      changelogCapability = "partial";
      changelogCompleteness = "incomplete";
      truncatedReason = truncatedReason ?? paged.reason;
      record.changelogComplete = false;
      break;
    }
    if (!paged.complete) {
      changelogCapability = "partial";
      changelogCompleteness = "incomplete";
      truncatedReason = truncatedReason ?? paged.reason ?? "incomplete_changelog";
      record.changelog = changelogItems(paged.items);
      record.changelogComplete = false;
      continue;
    }
    record.changelog = changelogItems(paged.items);
    record.changelogComplete = true;
  }
  endChangelogs();
  if (records.length === 0) changelogCompleteness = search.complete ? "empty" : "incomplete";

  const endWorklogs = markStage("worklogs");
  let worklogCapability = "retrieved";
  let worklogCompleteness = "complete";
  for (const record of records.slice(0, limits.enrichLimit)) {
    const paged = await paginateOffset({
      maxPages: 3,
      maxRecords: 50,
      pageSize: 50,
      identity: (item) => String(item.id),
      getItems: (page) => page.worklogs ?? [],
      getSourceCount: (page) => (page.worklogs ?? []).length,
      fetchPage: async (startAt, maxResults) => {
        const result = await call(
          `/rest/api/3/issue/${record.key}/worklog?startAt=${startAt}&maxResults=${maxResults}`,
          "worklog-collection",
          "GET",
          undefined,
          "worklog",
        );
        if (result.error) return { error: result.error.classification, worklogs: [] };
        return result.body;
      },
    });
    pageCount += paged.pages;
    if (paged.reason === "permission_denied" || paged.reason === "authentication_failed") {
      worklogCapability = "forbidden";
      worklogCompleteness = "forbidden";
      break;
    }
    if (paged.reason === "not_found") {
      worklogCapability = "unavailable";
      worklogCompleteness = "unavailable";
      break;
    }
    if (paged.reason === "malformed" || paged.reason === "partial") {
      worklogCapability = "unavailable";
      worklogCompleteness = "unavailable";
      record.worklogs = [];
      continue;
    }
    if (paged.reason === "deadline" || paged.reason === "retry_exceeds_deadline" || paged.reason === "stage_budget") {
      worklogCapability = "unavailable";
      worklogCompleteness = "incomplete";
      truncatedReason = truncatedReason ?? paged.reason;
      break;
    }
    record.worklogs = paged.items.map((item) => ({
      id: item.id,
      started: item.started,
      created: item.created,
      timeSpentSeconds: item.timeSpentSeconds,
    }));
    if (!paged.complete) {
      worklogCompleteness = "incomplete";
      truncatedReason = truncatedReason ?? paged.reason ?? "incomplete_worklog";
    }
  }
  endWorklogs();
  if (records.length === 0 && worklogCompleteness === "complete") worklogCompleteness = "empty";

  const endSla = markStage("sla");
  let slaCapability = desk ? "retrieved" : "unavailable";
  let slaCompleteness = desk ? "complete" : "unavailable";
  if (desk) {
    for (const record of records.slice(0, limits.enrichLimit)) {
      const paged = await paginateOffset({
        maxPages: 3,
        maxRecords: 50,
        pageSize: 50,
        identity: (item) => String(item.id ?? item.name),
        getItems: (page) => page.values ?? [],
        fetchPage: async (start, limit) => {
          const result = await call(
            `/rest/servicedeskapi/request/${record.key}/sla?start=${start}&limit=${limit}`,
            "sla-collection",
            "GET",
            undefined,
            "sla",
          );
          if (result.error) return { error: result.error.classification, values: [] };
          return withLastPage(result.body);
        },
      });
      pageCount += paged.pages;
      if (paged.reason === "permission_denied" || paged.reason === "authentication_failed") {
        slaCapability = "forbidden";
        slaCompleteness = "forbidden";
        break;
      }
      if (paged.reason === "not_found") {
        slaCapability = "unavailable";
        slaCompleteness = "unavailable";
        break;
      }
      if (paged.reason === "malformed" || paged.reason === "partial") {
        slaCapability = "unavailable";
        slaCompleteness = "unavailable";
        continue;
      }
      if (paged.reason === "deadline" || paged.reason === "retry_exceeds_deadline" || paged.reason === "stage_budget") {
        slaCapability = "unavailable";
        slaCompleteness = "incomplete";
        truncatedReason = truncatedReason ?? paged.reason;
        break;
      }
      record.sla = paged.items.flatMap((item) => slaCycles(item));
      if (!paged.complete) {
        slaCompleteness = "incomplete";
        truncatedReason = truncatedReason ?? paged.reason ?? "incomplete_sla";
      }
    }
  }
  endSla();

  const updatedTimes = records.map((item) => item.updated).filter(Boolean);
  const inconsistentSource = updatedTimes.some((stamp) => Date.parse(stamp) > Date.parse(importStartedAt));
  const searchComplete = search.complete === true;
  const changelogMandatoryOk = changelogCompleteness === "complete" || changelogCompleteness === "empty";
  const complete = searchComplete && changelogMandatoryOk && !truncatedReason;
  const extraction = {
    complete,
    truncatedReason: complete ? null : truncatedReason ?? search.reason ?? "incomplete",
    pageCount,
    retryCount,
    inconsistentSource,
    authorized: true,
    worklogCapability,
    slaCapability,
    changelogCapability,
    searchCompleteness: searchComplete ? (records.length === 0 ? "empty" : "complete") : "incomplete",
    changelogCompleteness,
    requestTypeCompleteness,
    worklogCompleteness,
    slaCompleteness,
    apiCallCount: apiCalls,
    stageDurations,
  };
  const importCompletedAt = new Date(clock.nowMs()).toISOString();
  const syntheticCount = records.filter((item) => item.syntheticOrigin).length;
  const observedCount = records.filter((item) => !item.syntheticOrigin && !item.originUnknown).length;
  const evidenceClass =
    records.length === 0 ? "observed" : syntheticCount === records.length ? "synthetic" : observedCount === records.length ? "observed" : "unknown";
  stages.push("normalize");
  const snapshot = buildSnapshot({
    issues: records,
    statuses,
    requestTypes,
    sourceProject,
    window,
    importConfiguration: {
      windowDays: parsed.windowDays,
      recordLimit: limits.recordLimit,
      pageLimit: limits.pageLimit,
      cohortPolicy: "open-during-window",
      includeWorklogs: true,
      includeSla: true,
    },
    extraction,
    importStartedAt,
    importCompletedAt,
    authorizedInstallationRef: installationRef,
    evidenceClass,
    transportAuthenticity: "live_api",
  });
  snapshot.limitations.push(
    `JQL used yyyy-MM-dd HH:mm in ${timeZone ?? "UTC with ±1 day padding"}; exact UTC window bounds are enforced during normalization.`,
  );
  const contract = validateSnapshot(snapshot);
  if (!contract.ok) {
    return failed("snapshot_contract", `Snapshot failed the os.1.0.0 contract at ${contract.path}: ${contract.message}`, { snapshot });
  }
  telemetry.push({
    event: complete ? "import.completed" : "import.partial",
    pageCount,
    retryCount,
    apiCalls,
    durationMs: clock.nowMs() - startedMs,
    cases: snapshot.cases.length,
  });
  return {
    status: complete ? "completed" : "partial",
    stage: stages[stages.length - 1],
    stages,
    telemetry,
    snapshot,
  };
}
