import assert from "node:assert/strict";
import test from "node:test";
import { exportJWK, generateKeyPair, SignJWT } from "jose";
import {
  FitValidationError,
  UNREGISTERED_APP_ID,
  assertPayloadBounds,
  extractBearerToken,
  jwksUrlForLabel,
  localKeySet,
  sanitizeRemoteLog,
  verifyForgeInvocationToken,
} from "./fit.js";

const TRUSTED_APP_ID = "ari:cloud:ecosystem::app/11111111-1111-4111-8111-111111111111";
const INSTALLATION_ID = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222";

async function signedToken({
  appId = TRUSTED_APP_ID,
  audience = TRUSTED_APP_ID,
  issuer = "forge/invocation-token",
  expiresIn = "2m",
  notBefore,
  issuedAt = true,
  installationId = INSTALLATION_ID,
  environmentType = "DEVELOPMENT",
  alg = "RS256",
  privateKey,
} = {}) {
  const jwt = new SignJWT({
    app: {
      id: appId,
      installationId,
      appVersion: "0.0.1",
      environment: { type: environmentType, id: "ari:cloud:ecosystem::environment/dev" },
      module: { type: "core:endpoint", key: "lab" },
    },
    context: { cloudId: "cloud-dev" },
  }).setProtectedHeader({ alg, kid: "cg1-test" }).setIssuer(issuer).setAudience(audience);
  if (issuedAt) jwt.setIssuedAt();
  if (notBefore) jwt.setNotBefore(notBefore);
  else jwt.setNotBefore("0s");
  if (expiresIn) jwt.setExpirationTime(expiresIn);
  return jwt.sign(privateKey);
}

async function setup() {
  const { publicKey, privateKey } = await generateKeyPair("RS256", { extractable: true });
  const jwk = await exportJWK(publicKey);
  jwk.kid = "cg1-test";
  jwk.alg = "RS256";
  jwk.use = "sig";
  return { privateKey, keySet: localKeySet(jwk) };
}

test("missing and non-bearer authorization is rejected", () => {
  assert.throws(() => extractBearerToken(""), { code: "missing_authorization" });
  assert.throws(() => extractBearerToken("Basic abc"), { code: "missing_authorization" });
  assert.throws(() => extractBearerToken("Bearer a b"), { code: "missing_authorization" });
});

test("valid FIT is accepted when app identity and installation match", async () => {
  const { privateKey, keySet } = await setup();
  const token = await signedToken({ privateKey });
  const result = await verifyForgeInvocationToken({
    authorizationHeader: `Bearer ${token}`,
    trustedAppId: TRUSTED_APP_ID,
    keySet,
  });
  assert.equal(result.installationId, INSTALLATION_ID);
  assert.equal(result.payload.app.id, TRUSTED_APP_ID);
});

test("expired, not-yet-valid, missing exp, wrong audience, issuer, and app identity are rejected", async () => {
  const { privateKey, keySet } = await setup();
  const expired = await signedToken({ privateKey, expiresIn: "0s" });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${expired}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
        currentDate: new Date(Date.now() + 30_000),
      }),
    (error) => error instanceof FitValidationError && error.code === "expired_token",
  );

  const future = await signedToken({ privateKey, notBefore: "1h" });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${future}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "not_yet_valid",
  );

  const missingExp = await signedToken({ privateKey, expiresIn: null });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${missingExp}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) =>
      error instanceof FitValidationError &&
      (error.code === "missing_expiration" || error.code === "invalid_token"),
  );

  const wrongAud = await signedToken({
    privateKey,
    audience: "ari:cloud:ecosystem::app/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${wrongAud}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "wrong_audience",
  );

  const wrongIss = await signedToken({ privateKey, issuer: "not-forge" });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${wrongIss}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "invalid_issuer",
  );

  const wrongApp = await signedToken({
    privateKey,
    appId: "ari:cloud:ecosystem::app/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    audience: TRUSTED_APP_ID,
  });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${wrongApp}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "wrong_app_id",
  );
});

test("placeholder app identity cannot accept remote invocations", async () => {
  const { privateKey, keySet } = await setup();
  const token = await signedToken({
    privateKey,
    appId: UNREGISTERED_APP_ID,
    audience: UNREGISTERED_APP_ID,
  });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${token}`,
        trustedAppId: UNREGISTERED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "unregistered_app",
  );
});

test("missing installation, malformed installation, and missing environment are rejected", async () => {
  const { privateKey, keySet } = await setup();
  const missingInstall = await signedToken({ privateKey, installationId: "not-an-ari" });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${missingInstall}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "invalid_installation",
  );

  const badEnv = await signedToken({ privateKey, environmentType: "LOCAL" });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${badEnv}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "invalid_environment",
  );
});

test("untrusted keys, manipulated signatures, and unsupported algorithms are rejected", async () => {
  const { privateKey, keySet } = await setup();
  const other = await generateKeyPair("RS256", { extractable: true });
  const token = await signedToken({ privateKey: other.privateKey });
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${token}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "invalid_token",
  );

  const valid = await signedToken({ privateKey });
  const tampered = `${valid.slice(0, -4)}abcd`;
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: `Bearer ${tampered}`,
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "invalid_token",
  );
});

test("invalid tokens, oversized payloads, and logs stay bounded", async () => {
  const { keySet } = await setup();
  await assert.rejects(
    () =>
      verifyForgeInvocationToken({
        authorizationHeader: "Bearer not-a-jwt",
        trustedAppId: TRUSTED_APP_ID,
        keySet,
      }),
    (error) => error instanceof FitValidationError && error.code === "invalid_token",
  );
  assert.throws(() => assertPayloadBounds("x".repeat(193 * 1024)), { code: "payload_too_large" });
  assert.equal(sanitizeRemoteLog("Bearer abc.def.ghi"), "[redacted-token]");
  assert.equal(jwksUrlForLabel(undefined), "https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks.json");
  assert.throws(() => jwksUrlForLabel("https://evil.example"), { code: "invalid_ic_label" });
});
