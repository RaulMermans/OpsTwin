import Resolver from "@forge/resolver";
import api, { invokeRemote, route } from "@forge/api";
import { classifyJiraResponse, classifyNetworkFailure } from "./jira/classify-response.js";

const resolver = new Resolver();
const REMOTE_KEY = "opstwin-simulation";
const COMPARE_PATH = "/api/integrations/atlassian/v1/compare";

function projectKeyFromContext(context) {
  const fromExtension = context?.extension?.project?.key;
  if (typeof fromExtension === "string" && fromExtension.trim()) {
    return fromExtension.trim();
  }
  return null;
}

function rejectBrowserProjectSubstitution(context, payload) {
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

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

resolver.define("getLabIdentity", (request) => {
  const projectKey = projectKeyFromContext(request.context);
  return {
    product: "OpsTwin for Jira",
    surface: "AI Transformation Lab",
    sprint: "CG-1",
    status: "Development integration",
    projectKey,
    accountIdPresent: Boolean(request.context?.accountId),
  };
});

resolver.define("getProjectSnapshot", async (request) => {
  const substitution = rejectBrowserProjectSubstitution(request.context, request.payload);
  if (substitution) return substitution;

  const projectKey = projectKeyFromContext(request.context);
  if (!projectKey) {
    return {
      status: "blocked",
      kind: "missing_context",
      message: "Forge did not provide a project key in the trusted invocation context.",
    };
  }

  let response;
  try {
    response = await api.asUser().requestJira(route`/rest/api/3/project/${projectKey}`);
  } catch (error) {
    const classified = classifyNetworkFailure(error);
    return { projectKey, status: "failed", classification: classified.kind, message: classified.message };
  }

  const body = await readJson(response);
  const classified = classifyJiraResponse(response.status, body, "project");
  return {
    projectKey,
    httpStatus: response.status,
    classification: classified.kind,
    message: classified.message,
    name: classified.kind === "ok" ? body.name : null,
    projectTypeKey: classified.kind === "ok" && typeof body.projectTypeKey === "string" ? body.projectTypeKey : null,
    id: classified.kind === "ok" ? body.id : null,
  };
});

resolver.define("getRequestTypes", async (request) => {
  const substitution = rejectBrowserProjectSubstitution(request.context, request.payload);
  if (substitution) return substitution;

  const projectKey = projectKeyFromContext(request.context);
  if (!projectKey) {
    return {
      status: "blocked",
      kind: "missing_context",
      message: "Forge did not provide a project key in the trusted invocation context.",
    };
  }

  let desksResponse;
  try {
    desksResponse = await api.asUser().requestJira(route`/rest/servicedeskapi/servicedesk`);
  } catch (error) {
    const classified = classifyNetworkFailure(error);
    return { projectKey, status: "failed", classification: classified.kind, message: classified.message };
  }

  const desksBody = await readJson(desksResponse);
  const desksClassified = classifyJiraResponse(desksResponse.status, desksBody, "servicedesk-collection");
  if (desksClassified.kind !== "ok" && desksClassified.kind !== "empty") {
    return {
      projectKey,
      httpStatus: desksResponse.status,
      classification: desksClassified.kind,
      message: desksClassified.message,
      requestTypes: [],
    };
  }

  const desk = Array.isArray(desksBody?.values)
    ? desksBody.values.find((item) => item && item.projectKey === projectKey)
    : null;
  if (!desk || desk.id === undefined || desk.id === null) {
    return {
      projectKey,
      httpStatus: desksResponse.status,
      classification: desksClassified.kind === "empty" ? "empty" : "not_found",
      message: "No service desk is visible for this project.",
      requestTypes: [],
    };
  }

  let typesResponse;
  try {
    typesResponse = await api.asUser().requestJira(route`/rest/servicedeskapi/servicedesk/${desk.id}/requesttype`);
  } catch (error) {
    const classified = classifyNetworkFailure(error);
    return { projectKey, status: "failed", classification: classified.kind, message: classified.message };
  }

  const typesBody = await readJson(typesResponse);
  const typesClassified = classifyJiraResponse(typesResponse.status, typesBody, "request-type-collection");
  const requestTypes =
    typesClassified.kind === "ok"
      ? typesBody.values.map((item) => ({ id: String(item.id), name: String(item.name) }))
      : [];
  return {
    projectKey,
    serviceDeskId: String(desk.id),
    httpStatus: typesResponse.status,
    classification: typesClassified.kind,
    message: typesClassified.message,
    requestTypes,
  };
});

resolver.define("runSyntheticComparison", async (request) => {
  const substitution = rejectBrowserProjectSubstitution(request.context, request.payload);
  if (substitution) return substitution;
  if (!projectKeyFromContext(request.context)) {
    return {
      status: "blocked",
      kind: "missing_context",
      message: "Forge did not provide a project key in the trusted invocation context.",
    };
  }

  const payload = request.payload && typeof request.payload === "object" ? request.payload : {};
  const body = {
    contractVersion: "cg1.v1",
    experimentId: "support-operations-synthetic",
    intervention: payload.intervention,
    extraCapacity: payload.extraCapacity,
    triageReductionPercent: payload.triageReductionPercent,
    runCount: payload.runCount ?? 5,
    baseSeed: payload.baseSeed ?? 20260716,
  };

  let remote;
  try {
    remote = await invokeRemote(REMOTE_KEY, {
      path: COMPARE_PATH,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (error) {
    const classified = classifyNetworkFailure(error);
    return { status: "failed", classification: classified.kind, message: classified.message };
  }

  const remoteBody = await readJson(remote);
  if (remote.status === 401) {
    return {
      status: "failed",
      classification: "authentication_failed",
      message: "The remote could not verify the Forge Invocation Token.",
    };
  }
  if (!remote.ok) {
    const message =
      remoteBody && remoteBody.error && typeof remoteBody.error.message === "string"
        ? remoteBody.error.message
        : "The remote comparison failed.";
    return {
      status: "failed",
      classification: remote.status === 408 ? "timeout" : "remote_error",
      httpStatus: remote.status,
      message,
    };
  }
  return { status: "ok", evidence: remoteBody };
});

export const handler = resolver.getDefinitions();
