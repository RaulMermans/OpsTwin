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
  installationId = INSTALLATION_ID,
  privateKey,
} = {}) {
  return new SignJWT({
    app: {
      id: appId,
      installationId,
      appVersion: "0.0.1",
      environment: { type: "DEVELOPMENT", id: "ari:cloud:ecosystem::environment/dev" },
      module: { type: "core:endpoint", key: "lab" },
    },
    context: { cloudId: "cloud-dev" },
  })
    .setProtectedHeader({ alg: "RS256", kid: "cg0-test" })
    .setIssuer(issuer)
    .setAudience(audience)
    .setIssuedAt()
    .setExpirationTime(expiresIn)
    .sign(privateKey);
}

async function setup() {
  const { publicKey, privateKey } = await generateKeyPair("RS256", { extractable: true });
  const jwk = await exportJWK(publicKey);
  jwk.kid = "cg0-test";
  jwk.alg = "RS256";
  jwk.use = "sig";
  return { privateKey, keySet: localKeySet(jwk) };
}

test("missing and non-bearer authorization is rejected", () => {
  assert.throws(() => extractBearerToken(""), { code: "missing_authorization" });
  assert.throws(() => extractBearerToken("Basic abc"), { code: "missing_authorization" });
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

test("expired, wrong audience, wrong issuer, and wrong app identity are rejected", async () => {
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
  assert.throws(() => assertPayloadBounds("x".repeat(65 * 1024)), { code: "payload_too_large" });
  assert.equal(sanitizeRemoteLog("Bearer abc.def.ghi"), "[redacted-token]");
  assert.equal(jwksUrlForLabel(undefined), "https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks.json");
});
