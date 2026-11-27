import { classifyJiraResponse, classifyNetworkFailure } from "./classify-response.js";
import { fetchWithRetry } from "./http.js";
import { paginateOffset, paginateToken } from "./paginate.js";
import { cohortJql, observationWindow } from "../operational/time.js";
import { statusRecord } from "../operational/normalize.js";
import { buildSnapshot } from "../operational/snapshot.js";

export const IMPORT_LIMITS = {
  recordLimit: 40,
  pageLimit: 8,
  pageSize: 20,
  changelogPageSize: 100,
  enrichLimit: 40,
};

const SEARCH_FIELDS = "created,resolutiondate,status,priority,issuetype,assignee,project,updated";

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

export function issueToRecord(issue, projectKey, requestTypeFieldId) {
  const fields = issue.fields ?? {};
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
    worklogs: [],
    sla: [],
    syntheticOrigin: Array.isArray(fields.labels) && fields.labels.includes("opstwin-synthetic"),
  };
}

export async function ingestOperationalData({ projectKey, installationRef, payload, now, requestJson }) {
  const parsed = parseWindowDays(payload);
  if (parsed.error) return failed("invalid_configuration", parsed.error);
  const window = observationWindow(parsed.windowDays, now);
  window.windowDays = parsed.windowDays;
  const importStartedAt = now.toISOString();
  const stages = [];
  const telemetry = [];
  let retryCount = 0;
  let pageCount = 0;

  async function call(path, schema, method = "GET", body) {
    const result = await fetchWithRetry(async () => {
      try {
        return await requestJson(path, method, body);
      } catch (error) {
        const classified = classifyNetworkFailure(error);
        return { status: 0, body: null, networkError: true, classification: classified };
      }
    });
    retryCount += result.retries ?? 0;
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

  stages.push("validate_project");
  telemetry.push({ event: "import.started", projectKey });
  const project = await call(`/rest/api/3/project/${projectKey}`, "project");
  if (project.error) return project.error;
  const sourceProject = {
    reference: `project:${project.body.key}`,
    key: project.body.key,
    name: project.body.name,
    serviceDeskId: null,
  };

  stages.push("service_desk");
  const desks = await call("/rest/servicedeskapi/servicedesk", "servicedesk-collection");
  const deskValues = Array.isArray(desks.body?.values) ? desks.body.values : [];
  const desk = desks.error ? null : deskValues.find((item) => item.projectKey === projectKey) ?? null;
  sourceProject.serviceDeskId = desk?.id !== undefined && desk?.id !== null ? String(desk.id) : null;

  let requestTypes = [];
  if (desk) {
    stages.push("request_types");
    const pagedTypes = await paginateOffset({
      maxPages: IMPORT_LIMITS.pageLimit,
      maxRecords: 100,
      pageSize: 50,
      identity: (item) => String(item.id),
      getItems: (page) => page.values ?? [],
      fetchPage: async (start, limit) => {
        const result = await call(`/rest/servicedeskapi/servicedesk/${desk.id}/requesttype?start=${start}&limit=${limit}`, "request-type-collection");
        if (result.error) return { error: result.error.classification, total: 0, values: [] };
        return result.body;
      },
    });
    pageCount += pagedTypes.pages;
    requestTypes = pagedTypes.items.map((item) => ({ requestTypeId: String(item.id), name: String(item.name) }));
  }

  stages.push("fields");
  const fields = await call("/rest/api/3/field", "unspecified");
  const requestTypeFieldId = fields.error ? null : findRequestTypeField(fields.body);

  stages.push("statuses");
  const statusBody = await call(`/rest/api/3/project/${projectKey}/statuses`, "unspecified");
  const statuses = [];
  if (!statusBody.error && Array.isArray(statusBody.body)) {
    for (const type of statusBody.body) {
      for (const status of type.statuses ?? []) statuses.push(statusRecord(status));
    }
  }

  stages.push("search");
  const jql = cohortJql(projectKey, window);
  const search = await paginateToken({
    maxPages: IMPORT_LIMITS.pageLimit,
    maxRecords: IMPORT_LIMITS.recordLimit,
    identity: (issue) => issue.id ?? issue.key,
    getItems: (page) => page.issues ?? [],
    getToken: (page) => page.nextPageToken ?? null,
    isComplete: (page) => page.isLast === true || !page.nextPageToken,
    fetchPage: async (token) => {
      const params = [`jql=${encodeURIComponent(jql)}`, `maxResults=${IMPORT_LIMITS.pageSize}`, `fields=${SEARCH_FIELDS}${requestTypeFieldId ? `,${requestTypeFieldId}` : ""}`, "expand=changelog"];
      if (token) params.push(`nextPageToken=${encodeURIComponent(token)}`);
      const result = await call(`/rest/api/3/search/jql?${params.join("&")}`, "issue-search");
      if (result.error) return { error: result.error.classification, issues: [] };
      return result.body;
    },
  });
  pageCount += search.pages;
  if (search.reason && search.reason !== "record_budget" && search.reason !== "page_budget" && search.items.length === 0 && !search.complete) {
    return failed(search.reason, "Issue search could not be completed.");
  }

  const records = [];
  for (const issue of search.items) {
    if ((issue.fields?.project?.key ?? issue.key?.split("-")[0]) !== projectKey) {
      telemetry.push({ event: "import.rejected", reason: "cross_project_record" });
      continue;
    }
    records.push(issueToRecord(issue, projectKey, requestTypeFieldId));
  }

  stages.push("changelogs");
  let changelogCapability = "retrieved";
  for (const record of records) {
    if (record.changelog.length > 0) continue;
    const paged = await paginateOffset({
      maxPages: 3,
      maxRecords: 200,
      pageSize: IMPORT_LIMITS.changelogPageSize,
      identity: (item) => item.id,
      getItems: (page) => changelogItems(page.values ?? page.histories ?? []),
      fetchPage: async (startAt, maxResults) => {
        const result = await call(`/rest/api/3/issue/${record.key}/changelog?startAt=${startAt}&maxResults=${maxResults}`, "unspecified");
        if (result.error) return { error: result.error.classification, values: [] };
        return result.body;
      },
    });
    pageCount += paged.pages;
    if (paged.reason === "permission_denied" || paged.reason === "authentication_failed") {
      changelogCapability = "forbidden";
      break;
    }
    record.changelog = paged.items;
  }

  stages.push("worklogs");
  let worklogCapability = "retrieved";
  for (const record of records.slice(0, IMPORT_LIMITS.enrichLimit)) {
    const paged = await paginateOffset({
      maxPages: 3,
      maxRecords: 50,
      pageSize: 50,
      identity: (item) => String(item.id),
      getItems: (page) => page.worklogs ?? page.values ?? [],
      fetchPage: async (startAt, maxResults) => {
        const result = await call(`/rest/api/3/issue/${record.key}/worklog?startAt=${startAt}&maxResults=${maxResults}`, "unspecified");
        if (result.error) return { error: result.error.classification, worklogs: [] };
        return result.body;
      },
    });
    pageCount += paged.pages;
    if (paged.reason === "permission_denied" || paged.reason === "authentication_failed") {
      worklogCapability = "forbidden";
      break;
    }
    if (paged.reason === "not_found") {
      worklogCapability = "unavailable";
      break;
    }
    record.worklogs = paged.items.map((item) => ({
      id: item.id,
      started: item.started,
      created: item.created,
      timeSpentSeconds: item.timeSpentSeconds,
    }));
  }

  stages.push("sla");
  let slaCapability = desk ? "retrieved" : "unavailable";
  if (desk) {
    for (const record of records.slice(0, IMPORT_LIMITS.enrichLimit)) {
      const result = await call(`/rest/servicedeskapi/request/${record.key}/sla`, "unspecified");
      if (result.error) {
        if (result.error.classification === "permission_denied" || result.error.classification === "authentication_failed") {
          slaCapability = "forbidden";
          break;
        }
        if (result.error.classification === "not_found") {
          slaCapability = "unavailable";
          break;
        }
        continue;
      }
      const values = result.body?.values ?? [];
      record.sla = values.map((item) => {
        const cycle = item.completedCycles?.[item.completedCycles.length - 1] ?? item.ongoingCycle;
        const elapsedMs = Number(cycle?.elapsedTime?.millis);
        return {
          id: item.id,
          name: item.name,
          startTime: cycle?.startTime?.iso8601 ?? cycle?.startTime,
          stopTime: cycle?.stopTime?.iso8601 ?? cycle?.stopTime,
          elapsedMinutes: Number.isFinite(elapsedMs) ? elapsedMs / 60000 : null,
          breached: Boolean(cycle?.breached ?? item.breached),
        };
      });
    }
  }

  const updatedTimes = records.map((item) => item.updated).filter(Boolean);
  const inconsistentSource = updatedTimes.some((stamp) => Date.parse(stamp) > Date.parse(importStartedAt));
  const complete = search.complete === true;
  const extraction = {
    complete,
    truncatedReason: complete ? null : search.reason ?? "incomplete",
    pageCount,
    retryCount,
    inconsistentSource,
    authorized: true,
    worklogCapability,
    slaCapability,
    changelogCapability,
  };
  stages.push("normalize");
  const snapshot = buildSnapshot({
    issues: records,
    statuses,
    requestTypes,
    sourceProject,
    window,
    importConfiguration: {
      windowDays: parsed.windowDays,
      recordLimit: IMPORT_LIMITS.recordLimit,
      pageLimit: IMPORT_LIMITS.pageLimit,
      cohortPolicy: "open-during-window",
      includeWorklogs: true,
      includeSla: true,
    },
    extraction,
    importStartedAt,
    importCompletedAt: now.toISOString(),
    authorizedInstallationRef: installationRef,
    evidenceClass: records.some((item) => item.syntheticOrigin) ? "synthetic" : "observed",
    transportAuthenticity: "live_api",
  });
  telemetry.push({ event: complete ? "import.completed" : "import.partial", pageCount, retryCount, cases: snapshot.cases.length });
  return {
    status: complete ? "completed" : "partial",
    stage: stages[stages.length - 1],
    stages,
    telemetry,
    snapshot,
  };
}
