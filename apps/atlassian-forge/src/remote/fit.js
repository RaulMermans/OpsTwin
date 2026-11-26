import { createLocalJWKSet, jwtVerify, errors } from "jose";

export const FIT_ISSUER = "forge/invocation-token";
export const UNREGISTERED_APP_ID = "ari:cloud:ecosystem::app/00000000-0000-4000-8000-000000000000";
export const COMMERCIAL_JWKS_URL = "https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks.json";
export const MAX_REMOTE_BYTES = 64 * 1024;

const IC_LABEL = /^[a-z0-9_-]{1,50}$/;

export class FitValidationError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "FitValidationError";
    this.code = code;
  }
}

export function jwksUrlForLabel(icLabel) {
  if (icLabel === undefined || icLabel === null || icLabel === "") {
    return COMMERCIAL_JWKS_URL;
  }
  if (typeof icLabel !== "string" || !IC_LABEL.test(icLabel)) {
    throw new FitValidationError("invalid_ic_label", "Isolated Cloud label is not a safe JWKS selector.");
  }
  return `https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks-${icLabel}.json`;
}

export function extractBearerToken(authorizationHeader) {
  if (typeof authorizationHeader !== "string" || authorizationHeader.trim() === "") {
    throw new FitValidationError("missing_authorization", "Authorization header is required.");
  }
  const match = /^Bearer\s+(\S+)/i.exec(authorizationHeader.trim());
  if (!match) {
    throw new FitValidationError("missing_authorization", "Authorization header must be a Bearer token.");
  }
  return match[1];
}

export function assertPayloadBounds(rawBody, limit = MAX_REMOTE_BYTES) {
  if (typeof rawBody !== "string" && !Buffer.isBuffer(rawBody)) {
    throw new FitValidationError("invalid_payload", "Remote body must be a string or buffer.");
  }
  const bytes = Buffer.byteLength(rawBody);
  if (bytes > limit) {
    throw new FitValidationError("payload_too_large", "Remote body exceeds the bounded payload limit.");
  }
  return bytes;
}

export function assertTrustedAppIdentity(payload, trustedAppId) {
  if (typeof trustedAppId !== "string" || !trustedAppId.startsWith("ari:cloud:ecosystem::app/")) {
    throw new FitValidationError("untrusted_app_id", "Trusted application identity is not configured.");
  }
  if (trustedAppId === UNREGISTERED_APP_ID) {
    throw new FitValidationError("unregistered_app", "Placeholder Forge app identity cannot accept remote invocations.");
  }
  if (payload?.app?.id !== trustedAppId) {
    throw new FitValidationError("wrong_app_id", "Forge application identity does not match the trusted app ID.");
  }
}

export function assertInstallationContext(payload) {
  const installationId = payload?.app?.installationId ?? payload?.app?.installation?.id;
  if (typeof installationId !== "string" || !installationId.startsWith("ari:cloud:ecosystem::installation/")) {
    throw new FitValidationError("invalid_installation", "Installation identity is missing from the Forge Invocation Token.");
  }
  return installationId;
}

export async function verifyForgeInvocationToken({
  authorizationHeader,
  trustedAppId,
  keySet,
  currentDate,
}) {
  const token = extractBearerToken(authorizationHeader);
  let payload;
  try {
    ({ payload } = await jwtVerify(token, keySet, {
      issuer: FIT_ISSUER,
      audience: trustedAppId,
      currentDate: currentDate ?? new Date(),
      clockTolerance: 5,
    }));
  } catch (error) {
    if (error instanceof errors.JWTExpired) {
      throw new FitValidationError("expired_token", "Forge Invocation Token has expired.");
    }
    if (error instanceof errors.JWTClaimValidationFailed && error.claim === "aud") {
      throw new FitValidationError("wrong_audience", "Forge Invocation Token audience does not match this app.");
    }
    if (error instanceof errors.JWTClaimValidationFailed && error.claim === "iss") {
      throw new FitValidationError("invalid_issuer", "Forge Invocation Token issuer is not trusted.");
    }
    throw new FitValidationError("invalid_token", "Forge Invocation Token could not be verified.");
  }
  assertTrustedAppIdentity(payload, trustedAppId);
  const installationId = assertInstallationContext(payload);
  return { payload, installationId };
}

export function localKeySet(jwk) {
  return createLocalJWKSet({ keys: [jwk] });
}

export function sanitizeRemoteLog(value) {
  if (typeof value !== "string") return "[redacted]";
  if (/bearer\s+/i.test(value) || value.split(".").length === 3) return "[redacted-token]";
  return value.slice(0, 80);
}
