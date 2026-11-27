import assert from "node:assert/strict";
import test from "node:test";
import {
  expectedAppId,
  isAppAri,
  isInstallationAri,
  REGISTERED_APP_ID,
  UNREGISTERED_APP_ID,
} from "./app-identity.js";

test("application identity is validated by format, not a single hardcoded test fixture", () => {
  const otherValid = "ari:cloud:ecosystem::app/aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
  assert.equal(isAppAri(REGISTERED_APP_ID), true);
  assert.equal(isAppAri(otherValid), true);
  assert.equal(isAppAri("ari:cloud:ecosystem::app/not-a-uuid"), false);
  assert.equal(isAppAri(UNREGISTERED_APP_ID), true);
  assert.equal(expectedAppId(otherValid), otherValid);
  assert.equal(expectedAppId(undefined), REGISTERED_APP_ID);
});

test("installation identity must be an installation ARI", () => {
  assert.equal(
    isInstallationAri("ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"),
    true,
  );
  assert.equal(isInstallationAri(REGISTERED_APP_ID), false);
  assert.equal(isInstallationAri("installation-1"), false);
});
