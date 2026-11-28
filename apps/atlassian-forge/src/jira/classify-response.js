function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasRequiredStrings(body, fields) {
  return fields.every((field) => typeof body[field] === "string" && body[field].trim() !== "");
}

function itemHas(item, fields) {
  return isRecord(item) && fields.every((field) => item[field] !== undefined && item[field] !== null);
}

function classifyArrayCollection(body, arrayKey, itemFields) {
  if (!isRecord(body) || !Array.isArray(body[arrayKey])) {
    return { kind: "malformed", message: `The collection envelope is missing a ${arrayKey} array.` };
  }
  if (body[arrayKey].length === 0) {
    return { kind: "empty", message: "The endpoint succeeded and returned an empty collection." };
  }
  const validCount = body[arrayKey].filter((item) => itemHas(item, itemFields)).length;
  if (validCount === 0) {
    return { kind: "malformed", message: "A collection item is missing required fields." };
  }
  if (validCount < body[arrayKey].length) {
    return { kind: "partial", message: "The collection contains a mix of valid and malformed items." };
  }
  return { kind: "ok", message: "The endpoint succeeded with a nonempty collection." };
}

function classifyCollection(body, itemFields) {
  return classifyArrayCollection(body, "values", itemFields);
}

const UNAUTHORIZED_SOURCE = {
  status: "blocked",
  kind: "unauthorized_source",
  message:
    "Current Jira permissions do not allow consuming source-linked evidence for this project. Re-authorize and import again.",
};

export function currentSourceAccessDecision(status, body, projectKey) {
  const classified = classifyJiraResponse(status, body, "project");
  if (classified.kind === "ok") {
    if (typeof body?.key === "string" && body.key === projectKey) {
      return null;
    }
    return UNAUTHORIZED_SOURCE;
  }
  if (
    classified.kind === "authentication_failed" ||
    classified.kind === "permission_denied" ||
    classified.kind === "not_found"
  ) {
    return UNAUTHORIZED_SOURCE;
  }
  return { status: "failed", classification: classified.kind, message: classified.message };
}

export function classifyNetworkFailure(error) {
  const message = error instanceof Error ? error.message : "The upstream request failed.";
  if (/timeout/i.test(message)) {
    return { kind: "timeout", message: "The upstream request timed out." };
  }
  return { kind: "network_failure", message: "The upstream request could not be completed." };
}

export function classifyJiraResponse(status, body, schema = "unspecified") {
  if (!Number.isInteger(status) || status < 100 || status > 599) {
    return { kind: "malformed", message: "HTTP status is not a valid integer status code." };
  }
  if (status === 401) {
    return { kind: "authentication_failed", message: "Authentication failed for this resource." };
  }
  if (status === 403) {
    return { kind: "permission_denied", message: "The caller cannot access this resource." };
  }
  if (status === 404) {
    return { kind: "not_found", message: "The resource does not exist or is hidden." };
  }
  if (status === 429) {
    return { kind: "rate_limited", message: "The API rejected the request because of rate limits." };
  }
  if (status >= 500) {
    return { kind: "upstream_failure", message: `The upstream service failed with HTTP ${status}.` };
  }
  if (status < 200 || status >= 300) {
    return { kind: "http_error", message: `Unexpected HTTP status ${status}.` };
  }

  if (schema === "project") {
    if (!isRecord(body) || !hasRequiredStrings(body, ["id", "key", "name"])) {
      return { kind: "malformed", message: "The project payload is missing required fields." };
    }
    return { kind: "ok", message: "The endpoint succeeded with a valid project object." };
  }

  if (schema === "myself") {
    if (!isRecord(body) || typeof body.timeZone !== "string" || body.timeZone.trim() === "") {
      return { kind: "malformed", message: "The caller profile is missing a timezone." };
    }
    return { kind: "ok", message: "The endpoint succeeded with a caller profile." };
  }

  if (schema === "servicedesk-collection") {
    return classifyCollection(body, ["id", "projectKey"]);
  }

  if (schema === "request-type-collection") {
    return classifyCollection(body, ["id", "name"]);
  }

  if (schema === "issue-search") {
    if (!isRecord(body) || !Array.isArray(body.issues)) {
      return { kind: "malformed", message: "The search payload is missing an issues array." };
    }
    if (body.nextPageToken !== undefined && body.nextPageToken !== null && typeof body.nextPageToken !== "string") {
      return { kind: "malformed", message: "Search continuation metadata is malformed." };
    }
    if (body.isLast !== undefined && typeof body.isLast !== "boolean") {
      return { kind: "malformed", message: "Search isLast must be a boolean when present." };
    }
    if (body.issues.length === 0) {
      return { kind: "empty", message: "The endpoint succeeded and returned no operational records." };
    }
    const valid = body.issues.every((item) => isRecord(item) && (item.id || item.key) && isRecord(item.fields));
    if (!valid) {
      return { kind: "malformed", message: "A search issue is missing identity or fields." };
    }
    return { kind: "ok", message: "The endpoint succeeded with a nonempty collection." };
  }

  if (schema === "changelog-collection") {
    return classifyCollection(body, ["id", "created"]);
  }

  if (schema === "worklog-collection") {
    return classifyArrayCollection(body, "worklogs", ["id"]);
  }

  if (schema === "sla-collection") {
    if (!isRecord(body) || !Array.isArray(body.values)) {
      return { kind: "malformed", message: "The SLA envelope is missing a values array." };
    }
    if (body.values.length === 0) {
      return { kind: "empty", message: "The endpoint succeeded and returned an empty collection." };
    }
    const valid = body.values.every((item) => isRecord(item) && item.id !== undefined && item.id !== null);
    if (!valid) {
      return { kind: "malformed", message: "An SLA item is missing required fields." };
    }
    return { kind: "ok", message: "The endpoint succeeded with a nonempty collection." };
  }

  if (schema === "project-statuses") {
    if (!Array.isArray(body)) {
      return { kind: "malformed", message: "Project statuses must be an array of issue-type status groups." };
    }
    if (body.length === 0) {
      return { kind: "empty", message: "The endpoint succeeded and returned no statuses." };
    }
    return { kind: "ok", message: "The endpoint succeeded with project statuses." };
  }

  if (schema === "field-metadata") {
    if (!Array.isArray(body)) {
      return { kind: "malformed", message: "Field metadata must be an array." };
    }
    if (body.length === 0) {
      return { kind: "empty", message: "The endpoint succeeded and returned no fields." };
    }
    const valid = body.every((item) => isRecord(item) && typeof item.id === "string");
    if (!valid) {
      return { kind: "malformed", message: "A field record is missing an id." };
    }
    return { kind: "ok", message: "The endpoint succeeded with field metadata." };
  }

  if (schema === "unspecified") {
    return { kind: "malformed", message: "Operational endpoints require an explicit response schema." };
  }

  if (!isRecord(body) && !Array.isArray(body)) {
    return { kind: "malformed", message: "The response body is not a JSON object or array." };
  }
  return { kind: "ok", message: "The endpoint succeeded with a JSON payload." };
}
