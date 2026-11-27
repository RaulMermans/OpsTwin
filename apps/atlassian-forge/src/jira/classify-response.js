function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasRequiredStrings(body, fields) {
  return fields.every((field) => typeof body[field] === "string" && body[field].trim() !== "");
}

function classifyCollection(body, itemFields) {
  if (!isRecord(body) || !Array.isArray(body.values)) {
    return { kind: "malformed", message: "The collection envelope is missing a values array." };
  }
  if (body.values.length === 0) {
    return { kind: "empty", message: "The endpoint succeeded and returned an empty collection." };
  }
  const valid = body.values.every(
    (item) => isRecord(item) && itemFields.every((field) => item[field] !== undefined && item[field] !== null),
  );
  if (!valid) {
    return { kind: "malformed", message: "A collection item is missing required fields." };
  }
  return { kind: "ok", message: "The endpoint succeeded with a nonempty collection." };
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
    if (body.issues.length === 0) {
      return { kind: "empty", message: "The endpoint succeeded and returned no operational records." };
    }
    return { kind: "ok", message: "The endpoint succeeded with a nonempty collection." };
  }

  if (!isRecord(body) && !Array.isArray(body)) {
    return { kind: "malformed", message: "The response body is not a JSON object or array." };
  }
  return { kind: "ok", message: "The endpoint succeeded with a JSON payload." };
}
