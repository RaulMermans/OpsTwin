#!/usr/bin/env node
/**
 * Dry-run by default. Writes require --execute --i-authorize-writes plus
 * JIRA_EMAIL and JIRA_API_TOKEN in the environment. Allowlisted to OPS on
 * opstwin-dev.atlassian.net. Maximum eight issues. Idempotent on summary+labels.
 */
const ALLOWED_SITES = ["opstwin-dev.atlassian.net"];
const ALLOWED_PROJECTS = ["OPS"];
const MAX_ISSUES = 8;
const LABEL = "opstwin-synthetic";
const SUMMARY_PREFIX = "[OpsTwin synthetic]";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const key = process.argv[index];
  if (key.startsWith("--")) {
    const name = key.slice(2);
    const next = process.argv[index + 1];
    if (!next || next.startsWith("--")) args.set(name, true);
    else {
      args.set(name, next);
      index += 1;
    }
  }
}

const site = String(args.get("site") ?? "");
const project = String(args.get("project") ?? "");
const count = Math.min(MAX_ISSUES, Number(args.get("count") ?? 3));
const execute = args.get("execute") === true;
const authorized = args.get("i-authorize-writes") === true;
const cleanup = args.get("cleanup") === true;

if (!ALLOWED_SITES.includes(site) || !ALLOWED_PROJECTS.includes(project)) {
  console.error("Rejected: site/project are not on the synthetic sandbox allowlist.");
  process.exit(2);
}
if (!Number.isInteger(count) || count < 1) {
  console.error("Rejected: count must be a positive integer.");
  process.exit(2);
}

const cases = [
  { summary: `${SUMMARY_PREFIX} access request`, transitions: ["In Progress", "Done"], note: "resolve after create" },
  { summary: `${SUMMARY_PREFIX} open incident`, transitions: ["In Progress"], note: "leave open" },
  { summary: `${SUMMARY_PREFIX} reopen drill`, transitions: ["Done"], note: "reopen after resolve if the workflow allows it" },
  { summary: `${SUMMARY_PREFIX} waiting request`, transitions: [], note: "created only" },
  { summary: `${SUMMARY_PREFIX} second open incident`, transitions: ["In Progress"], note: "leave open" },
].slice(0, count);

const plan = {
  site,
  project,
  count,
  issueTypeDiscovery: "execute-time project createmeta; not hardcoded Task",
  requestTypes: ["Get IT help", "Report a system problem", "Request admin access"],
  labels: [LABEL, "opstwin-cg2"],
  summaryPrefix: SUMMARY_PREFIX,
  cases,
  execute,
  cleanup,
  estimatedApiOperations: count * 4,
  note: "Jira Cloud will stamp current timestamps. This cannot fabricate months of changelog history.",
};

console.log(JSON.stringify(plan, null, 2));
if (!execute) {
  console.log("Dry-run only. No issues were created or deleted.");
  process.exit(0);
}
if (cleanup) {
  console.error("Cleanup requires an explicit future confirmation flag and was not executed.");
  process.exit(2);
}
if (!authorized) {
  console.error("Refusing to execute writes without --i-authorize-writes.");
  process.exit(2);
}

const email = process.env.JIRA_EMAIL;
const token = process.env.JIRA_API_TOKEN;
if (!email || !token) {
  console.error("Rejected: JIRA_EMAIL and JIRA_API_TOKEN must be set in the owner environment.");
  process.exit(2);
}

const auth = Buffer.from(`${email}:${token}`).toString("base64");
const base = `https://${site}`;

async function jira(method, path, body) {
  const response = await fetch(`${base}${path}`, {
    method,
    headers: {
      authorization: `Basic ${auth}`,
      accept: "application/json",
      "content-type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let parsed = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`${method} ${path} failed: ${response.status} ${text.slice(0, 300)}`);
  }
  return parsed;
}

const existing = await jira("GET", `/rest/api/3/search/jql?jql=${encodeURIComponent(`project = "${project}" AND labels = "${LABEL}" ORDER BY key ASC`)}&maxResults=50&fields=summary,labels`);
const bySummary = new Map((existing.issues ?? []).map((issue) => [issue.fields?.summary, issue]));
const created = [];
const reused = [];
const meta = await jira("GET", `/rest/api/3/issue/createmeta?projectKeys=${encodeURIComponent(project)}&expand=projects.issuetypes`);
const types = meta.projects?.[0]?.issuetypes ?? [];
const issueType = types.find((entry) => entry && entry.subtask !== true);
if (!issueType?.id) {
  throw new Error("No creatable issue type was discovered for the allowlisted project.");
}
for (const item of cases) {
  const found = bySummary.get(item.summary);
  if (found) {
    reused.push(found.key);
    continue;
  }
  const issue = await jira("POST", "/rest/api/3/issue", {
    fields: {
      project: { key: project },
      summary: item.summary,
      issuetype: { id: issueType.id },
      labels: [LABEL, "opstwin-cg2"],
    },
  });
  created.push(issue.key);
  for (const name of item.transitions) {
    const available = await jira("GET", `/rest/api/3/issue/${issue.key}/transitions`);
    const match = (available.transitions ?? []).find((transition) => transition.name === name);
    if (!match) continue;
    await jira("POST", `/rest/api/3/issue/${issue.key}/transitions`, { transition: { id: match.id } });
  }
}

console.log(JSON.stringify({ created, reused, remaining: count - created.length - reused.length }, null, 2));
