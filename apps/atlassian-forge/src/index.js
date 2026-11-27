import Resolver from "@forge/resolver";
import api, { invokeRemote, route } from "@forge/api";
import { classifyJiraResponse, classifyNetworkFailure } from "./jira/classify-response.js";
import { installationRefFromContext, projectKeyFromContext, rejectBrowserProjectSubstitution } from "./jira/context.js";
import { ingestOperationalData } from "./jira/ingest.js";
import { generateSynthetic } from "./operational/synthetic.js";

const resolver = new Resolver();
const REMOTE_KEY = "opstwin-simulation";
const COMPARE_PATH = "/api/integrations/atlassian/v1/compare";

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function headerMap(response) {
  const retryAfter = response.headers?.get?.("retry-after") ?? response.headers?.["retry-after"];
  return retryAfter ? { "retry-after": retryAfter } : {};
}

async function requestJson(path, method = "GET", body) {
  const options = { method };
  if (body) {
    options.headers = { "content-type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const response = await api.asUser().requestJira(route`${path}`, options);
  return { status: response.status, body: await readJson(response), headers: headerMap(response) };
}

resolver.define("getLabIdentity", (request) => {
  const projectKey = projectKeyFromContext(request.context);
  return {
    product: "OpsTwin for Jira",
    surface: "AI Transformation Lab",
    sprint: "CG-2",
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

resolver.define("importOperationalSnapshot", async (request) => {
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
  try {
    return await ingestOperationalData({
      projectKey,
      installationRef: installationRefFromContext(request.context),
      payload: request.payload && typeof request.payload === "object" ? request.payload : {},
      now: new Date(),
      requestJson,
    });
  } catch (error) {
    const classified = classifyNetworkFailure(error);
    return { status: "failed", classification: classified.kind, message: classified.message };
  }
});

resolver.define("loadSyntheticOperationalDemo", (request) => {
  const substitution = rejectBrowserProjectSubstitution(request.context, request.payload);
  if (substitution) return substitution;
  if (!projectKeyFromContext(request.context)) {
    return {
      status: "blocked",
      kind: "missing_context",
      message: "Forge did not provide a project key in the trusted invocation context.",
    };
  }
  const profile = request.payload?.profile === "stress" ? "stress" : "golden";
  return {
    status: "completed",
    mode: "synthetic-demo",
    snapshot: generateSynthetic(profile, 20261127, new Date("2026-10-15T00:00:00.000Z")),
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
