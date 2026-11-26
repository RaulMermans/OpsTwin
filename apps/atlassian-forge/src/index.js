import Resolver from "@forge/resolver";
import api, { route } from "@forge/api";
import { classifyJiraResponse } from "./jira/classify-response.js";

const resolver = new Resolver();

function projectKeyFromContext(context) {
  const fromExtension = context?.extension?.project?.key;
  if (typeof fromExtension === "string" && fromExtension.trim()) {
    return fromExtension.trim();
  }
  return null;
}

resolver.define("getLabIdentity", (request) => {
  const projectKey = projectKeyFromContext(request.context);
  return {
    product: "OpsTwin for Jira",
    surface: "AI Transformation Lab",
    sprint: "CG-0",
    status: "Development integration",
    projectKey,
    accountIdPresent: Boolean(request.context?.accountId),
  };
});

resolver.define("getProjectSnapshot", async (request) => {
  const projectKey = projectKeyFromContext(request.context);
  if (!projectKey) {
    return {
      status: "blocked",
      kind: "missing_context",
      message: "Forge did not provide a project key in the trusted invocation context.",
    };
  }

  const response = await api.asUser().requestJira(route`/rest/api/3/project/${projectKey}`);
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  const classified = classifyJiraResponse(response.status, body);
  return {
    projectKey,
    httpStatus: response.status,
    classification: classified.kind,
    name: classified.kind === "ok" && body && typeof body.name === "string" ? body.name : null,
    projectTypeKey:
      classified.kind === "ok" && body && typeof body.projectTypeKey === "string"
        ? body.projectTypeKey
        : null,
  };
});

export const handler = resolver.getDefinitions();
