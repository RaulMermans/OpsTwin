const WINDOW_DAYS = new Set([30, 60, 90]);

export function isUtcIso(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value);
}

export function parseTimestamp(value) {
  if (value === null || value === undefined || value === "") {
    return { ok: false, reason: "missing", utcMs: null, utcIso: null, source: value ?? null };
  }
  if (typeof value !== "string") {
    return { ok: false, reason: "invalid", utcMs: null, utcIso: null, source: value };
  }
  const ms = Date.parse(value);
  if (!Number.isFinite(ms)) {
    return { ok: false, reason: "invalid", utcMs: null, utcIso: null, source: value };
  }
  return { ok: true, reason: null, utcMs: ms, utcIso: new Date(ms).toISOString(), source: value };
}

export function durationMinutes(startIso, endIso) {
  const start = parseTimestamp(startIso);
  const end = parseTimestamp(endIso);
  if (!start.ok || !end.ok) return { ok: false, minutes: null, reason: "invalid" };
  const delta = end.utcMs - start.utcMs;
  if (delta < 0) return { ok: false, minutes: null, reason: "negative" };
  return { ok: true, minutes: delta / 60000, reason: null };
}

export function observationWindow(windowDays, now = new Date()) {
  if (!WINDOW_DAYS.has(windowDays)) {
    throw new Error("Observation window must be 30, 60, or 90 days.");
  }
  const endMs = now.getTime();
  const startMs = endMs - windowDays * 24 * 60 * 60 * 1000;
  return {
    start: new Date(startMs).toISOString(),
    end: new Date(endMs).toISOString(),
    convention: "closed-start-open-end-utc",
    windowDays,
  };
}

export function inWindow(iso, window) {
  const parsed = parseTimestamp(iso);
  if (!parsed.ok) return false;
  const start = Date.parse(window.start);
  const end = Date.parse(window.end);
  return parsed.utcMs >= start && parsed.utcMs < end;
}

export function cohortJql(projectKey, window) {
  const start = window.start;
  const end = window.end;
  return `project = "${projectKey}" AND created < "${end}" AND (resolved IS EMPTY OR resolved >= "${start}")`;
}
