function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isEmptyDataset(body) {
  if (body === null || body === undefined) return true;
  if (Array.isArray(body)) return body.length === 0;
  if (!isRecord(body)) return false;
  if (Array.isArray(body.values) && body.values.length === 0) return true;
  if (Array.isArray(body.issues) && body.issues.length === 0) return true;
  if (typeof body.total === "number" && body.total === 0) return true;
  return false;
}

export function classifyJiraResponse(status, body) {
  if (!Number.isInteger(status) || status < 100 || status > 599) {
    return { kind: "malformed", message: "HTTP status is not a valid integer status code." };
  }
  if (status === 401 || status === 403) {
    return { kind: "permission_denied", message: "The caller cannot access this resource." };
  }
  if (status === 404) {
    return { kind: "not_found", message: "The resource does not exist or is hidden." };
  }
  if (status === 429) {
    return { kind: "rate_limited", message: "The API rejected the request because of rate limits." };
  }
  if (status < 200 || status >= 300) {
    return { kind: "http_error", message: `Unexpected HTTP status ${status}.` };
  }
  if (isEmptyDataset(body)) {
    return { kind: "empty", message: "The endpoint succeeded and returned no operational records." };
  }
  if (!isRecord(body) && !Array.isArray(body)) {
    return { kind: "malformed", message: "The response body is not a JSON object or array." };
  }
  return { kind: "ok", message: "The endpoint succeeded with at least one record or object." };
}
