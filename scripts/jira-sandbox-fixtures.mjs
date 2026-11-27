#!/usr/bin/env node
/**
 * Dry-run by default. Never creates issues unless --execute is passed after
 * --site and --project match the allowlist. Do not run --execute without owner approval.
 */
const ALLOWED_SITES = ["opstwin-dev.atlassian.net"];
const ALLOWED_PROJECTS = ["OPS"];
const MAX_ISSUES = 8;
const LABEL = "opstwin-synthetic";

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
const cleanup = args.get("cleanup") === true;

if (!ALLOWED_SITES.includes(site) || !ALLOWED_PROJECTS.includes(project)) {
  console.error("Rejected: site/project are not on the synthetic sandbox allowlist.");
  process.exit(2);
}
if (!Number.isInteger(count) || count < 1) {
  console.error("Rejected: count must be a positive integer.");
  process.exit(2);
}

const plan = {
  site,
  project,
  count,
  requestTypes: ["Get IT help", "Report a system problem", "Request admin access"],
  labels: [LABEL, "opstwin-cg2"],
  summaryPrefix: "[OpsTwin synthetic]",
  execute,
  cleanup,
  estimatedApiOperations: count * 3,
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
console.error("Refusing to execute writes from this agent session. Owner must run a reviewed command locally.");
process.exit(2);
