import ResolverModule from "@forge/resolver";
import api, { invokeRemote, route } from "@forge/api";
import { classifyJiraResponse, classifyNetworkFailure } from "./jira/classify-response.js";
import { installationRefFromContext, projectKeyFromContext, rejectBrowserProjectSubstitution } from "./jira/context.js";
import { ingestOperationalData } from "./jira/ingest.js";
import { describeJiraPath } from "./jira/route.js";
import { generateSynthetic } from "./operational/synthetic.js";
import { validateEconomicEvidence, validateTransformEvidence } from "./remote/evidence.js";

const Resolver = typeof ResolverModule === "function" ? ResolverModule : ResolverModule.default;
const resolver = new Resolver();
const REMOTE_KEY = "opstwin-simulation";
const COMPARE_PATH = "/api/integrations/atlassian/v1/compare";
const CALIBRATE_PATH = "/api/integrations/atlassian/v1/calibrate";
const TRANSFORM_PATH = "/api/integrations/atlassian/v1/transform";
const ECONOMICS_PATH = "/api/integrations/atlassian/v1/evaluate-economics";

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
  const described = describeJiraPath(path);
  if (described.kind === "unsupported") {
    throw new Error(`Unsupported Jira path ${described.pathname}`);
  }
  const p = described.params;
  const routes = {
    myself: () => route`/rest/api/3/myself`,
    field: () => route`/rest/api/3/field`,
    servicedesk: () =>
      p.start
        ? route`/rest/servicedeskapi/servicedesk?start=${p.start}&limit=${p.limit}`
        : route`/rest/servicedeskapi/servicedesk`,
    "search-jql": () =>
      method === "POST"
        ? route`/rest/api/3/search/jql`
        : p.nextPageToken
          ? route`/rest/api/3/search/jql?jql=${p.jql}&maxResults=${p.maxResults}&fields=${p.fields}&expand=${p.expand}&nextPageToken=${p.nextPageToken}`
          : route`/rest/api/3/search/jql?jql=${p.jql}&maxResults=${p.maxResults}&fields=${p.fields}&expand=${p.expand}`,
    "project-statuses": () => route`/rest/api/3/project/${described.projectKey}/statuses`,
    project: () => route`/rest/api/3/project/${described.projectKey}`,
    changelog: () => route`/rest/api/3/issue/${described.issueKey}/changelog?startAt=${p.startAt}&maxResults=${p.maxResults}`,
    worklog: () => route`/rest/api/3/issue/${described.issueKey}/worklog?startAt=${p.startAt}&maxResults=${p.maxResults}`,
    "request-type": () =>
      route`/rest/servicedeskapi/servicedesk/${described.serviceDeskId}/requesttype?start=${p.start}&limit=${p.limit}`,
    sla: () =>
      p.start
        ? route`/rest/servicedeskapi/request/${described.issueKey}/sla?start=${p.start}&limit=${p.limit}`
        : route`/rest/servicedeskapi/request/${described.issueKey}/sla`,
  };
  const response = await api.asUser().requestJira(routes[described.kind](), options);
  return { status: response.status, body: await readJson(response), headers: headerMap(response) };
}

resolver.define("getLabIdentity", (request) => {
  const projectKey = projectKeyFromContext(request.context);
  return {
    product: "OpsTwin for Jira",
    surface: "AI Transformation Lab",
    sprint: "CG-6",
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
    return {
      status: "failed",
      classification: classified.kind,
      message: error instanceof Error ? error.message : classified.message,
    };
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

resolver.define("runSyntheticCalibration", async (request) => {
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
    contractVersion: "cg3.v1",
    fixtureId:
      payload.fixtureId === "cg5-hybrid-support"
        ? "cg5-hybrid-support"
        : payload.fixtureId === "cg3-partially-observable"
          ? "cg3-partially-observable"
          : "cg3-golden-analytical",
    approveLabAssumptions: payload.approveLabAssumptions === true,
    randomSeed: payload.randomSeed ?? 20260327,
  };
  let remote;
  try {
    remote = await invokeRemote(REMOTE_KEY, {
      path: CALIBRATE_PATH,
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
        : "The remote calibration failed.";
    return {
      status: "failed",
      classification: remote.status === 408 ? "timeout" : "remote_error",
      httpStatus: remote.status,
      message,
    };
  }
  return { status: "ok", evidence: remoteBody, mode: "synthetic-demo" };
});

resolver.define("runTransformationExperiment", async (request) => {
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
  const fixtureId =
    payload.fixtureId === "cg5-hybrid-support"
      ? "cg5-hybrid-support"
      : payload.fixtureId === "cg3-partially-observable"
        ? "cg3-partially-observable"
        : "cg3-golden-analytical";
  const multi = payload.contractVersion === "cg5.v1" && Array.isArray(payload.alternatives);
  const body = multi
    ? {
        contractVersion: "cg5.v1",
        fixtureId,
        approveLabAssumptions: payload.approveLabAssumptions === true,
        randomSeed: payload.randomSeed ?? 20260327,
        alternatives: payload.alternatives,
        execution: payload.execution ?? { itemCount: 20, runCount: 5, baseSeed: 20261127 },
        experimentId: payload.experimentId,
        requestId: payload.requestId,
      }
    : {
        contractVersion: "cg4.v1",
        fixtureId,
        approveLabAssumptions: payload.approveLabAssumptions === true,
        randomSeed: payload.randomSeed ?? 20260327,
        intervention: payload.intervention,
        execution: payload.execution ?? { itemCount: 40, runCount: 5, baseSeed: 20261127 },
      };
  let remote;
  try {
    remote = await invokeRemote(REMOTE_KEY, {
      path: TRANSFORM_PATH,
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
        : "The transformation experiment failed.";
    return {
      status: "failed",
      classification: remote.status === 408 ? "timeout" : "remote_error",
      httpStatus: remote.status,
      message,
    };
  }
  const validated = validateTransformEvidence(remoteBody, {
    requestId: payload.requestId,
    experimentId: payload.experimentId,
    alternativeIds: multi ? payload.alternatives?.map((item) => item.alternativeId) : undefined,
  });
  if (!validated.ok) {
    return { status: "failed", classification: "invalid_response", message: validated.message };
  }
  return { status: "ok", evidence: remoteBody };
});

resolver.define("runEconomicEvaluation", async (request) => {
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
  if (payload.evidence?.experimentStatus === "failed") {
    return {
      status: "failed",
      classification: "invalid_request",
      message: "A failed experiment cannot produce an economic comparison.",
    };
  }
  const body = {
    contractVersion: "cg6.v1",
    fixtureId: payload.fixtureId,
    alternatives: payload.alternatives,
    execution: payload.execution,
    experimentIdentity: payload.experimentIdentity,
    evidence: payload.evidence,
    assumptions: payload.assumptions,
    constraints: payload.constraints ?? {},
    explore: payload.explore,
  };
  let remote;
  try {
    remote = await invokeRemote(REMOTE_KEY, {
      path: ECONOMICS_PATH,
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
        : "The economic evaluation failed.";
    return {
      status: "failed",
      classification: remote.status === 408 ? "timeout" : "remote_error",
      httpStatus: remote.status,
      message,
    };
  }
  const validated = validateEconomicEvidence(remoteBody, {
    experimentIdentity: payload.experimentIdentity,
  });
  if (!validated.ok) {
    return { status: "failed", classification: "invalid_response", message: validated.message };
  }
  return { status: "ok", evidence: remoteBody };
});

export const handler = resolver.getDefinitions();
