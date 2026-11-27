export function projectKeyFromContext(context) {
  const fromExtension = context?.extension?.project?.key;
  if (typeof fromExtension === "string" && fromExtension.trim()) {
    return fromExtension.trim();
  }
  return null;
}

export function installationRefFromContext(context) {
  const installation = context?.installation?.id ?? context?.installContext ?? null;
  return typeof installation === "string" && installation.trim() ? installation.trim() : null;
}

export function rejectBrowserProjectSubstitution(context, payload) {
  const trusted = projectKeyFromContext(context);
  const supplied = payload && typeof payload === "object" ? payload.projectKey : undefined;
  if (typeof supplied === "string" && supplied.trim() && supplied.trim() !== trusted) {
    return {
      status: "blocked",
      kind: "untrusted_project",
      message: "Project identity must come from Forge context, not from the browser.",
    };
  }
  return null;
}

export function assertIssueInProject(issue, projectKey) {
  const key = issue?.key ?? "";
  const project = issue?.fields?.project?.key ?? issue?.project?.key ?? (typeof key === "string" && key.includes("-") ? key.split("-")[0] : null);
  return project === projectKey;
}
