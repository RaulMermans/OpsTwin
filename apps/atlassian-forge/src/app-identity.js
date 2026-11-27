export const REGISTERED_APP_ID = "ari:cloud:ecosystem::app/73670daa-a329-4491-8a96-89bf239b203b";
export const UNREGISTERED_APP_ID = "ari:cloud:ecosystem::app/00000000-0000-4000-8000-000000000000";

const APP_ARI = /^ari:cloud:ecosystem::app\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const INSTALLATION_ARI =
  /^ari:cloud:ecosystem::installation\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isAppAri(value) {
  return typeof value === "string" && APP_ARI.test(value);
}

export function isInstallationAri(value) {
  return typeof value === "string" && INSTALLATION_ARI.test(value);
}

export function expectedAppId(configured = process.env.OPSTWIN_FORGE_APP_ID) {
  if (typeof configured === "string" && configured.trim()) {
    return configured.trim();
  }
  return REGISTERED_APP_ID;
}
