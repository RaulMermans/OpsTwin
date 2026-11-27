export function describeJiraPath(path) {
  const q = path.indexOf("?");
  const pathname = q >= 0 ? path.slice(0, q) : path;
  const query = q >= 0 ? path.slice(q + 1) : "";
  const s = pathname.split("/").filter(Boolean);
  const p = Object.fromEntries(new URLSearchParams(query));
  if (pathname === "/rest/api/3/myself") return { kind: "myself", pathname, params: p };
  if (pathname === "/rest/api/3/field") return { kind: "field", pathname, params: p };
  if (pathname === "/rest/servicedeskapi/servicedesk") return { kind: "servicedesk", pathname, params: p };
  if (s[0] === "rest" && s[1] === "api" && s[2] === "3" && s[3] === "search" && s[4] === "jql") {
    return { kind: "search-jql", pathname, params: p, issueKey: null };
  }
  if (s[0] === "rest" && s[1] === "api" && s[2] === "3" && s[3] === "project" && s[5] === "statuses") {
    return { kind: "project-statuses", pathname, params: p, projectKey: s[4] };
  }
  if (s[0] === "rest" && s[1] === "api" && s[2] === "3" && s[3] === "project" && s.length === 5) {
    return { kind: "project", pathname, params: p, projectKey: s[4] };
  }
  if (s[0] === "rest" && s[1] === "api" && s[2] === "3" && s[3] === "issue" && s[5] === "changelog") {
    return { kind: "changelog", pathname, params: p, issueKey: s[4] };
  }
  if (s[0] === "rest" && s[1] === "api" && s[2] === "3" && s[3] === "issue" && s[5] === "worklog") {
    return { kind: "worklog", pathname, params: p, issueKey: s[4] };
  }
  if (s[0] === "rest" && s[1] === "servicedeskapi" && s[2] === "servicedesk" && s[4] === "requesttype") {
    return { kind: "request-type", pathname, params: p, serviceDeskId: s[3] };
  }
  if (s[0] === "rest" && s[1] === "servicedeskapi" && s[2] === "request" && s[4] === "sla") {
    return { kind: "sla", pathname, params: p, issueKey: s[3] };
  }
  return { kind: "unsupported", pathname, params: p };
}
