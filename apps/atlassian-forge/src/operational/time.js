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

export function jqlDateTime(iso, timeZone = "UTC") {
  const parsed = parseTimestamp(iso);
  if (!parsed.ok) return null;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(parsed.utcMs));
  const get = (type) => parts.find((part) => part.type === type)?.value;
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}

export function jqlQueryWindow(window, timeZone) {
  if (timeZone) {
    return {
      start: jqlDateTime(window.start, timeZone),
      end: jqlDateTime(window.end, timeZone),
      padded: false,
      timeZone,
    };
  }
  const startMs = Date.parse(window.start) - 24 * 60 * 60 * 1000;
  const endMs = Date.parse(window.end) + 24 * 60 * 60 * 1000;
  return {
    start: jqlDateTime(new Date(startMs).toISOString(), "UTC"),
    end: jqlDateTime(new Date(endMs).toISOString(), "UTC"),
    padded: true,
    timeZone: "UTC",
  };
}

export function overlapsObservationWindow(createdIso, resolvedIso, window) {
  const created = parseTimestamp(createdIso);
  if (!created.ok) return false;
  const start = Date.parse(window.start);
  const end = Date.parse(window.end);
  if (created.utcMs >= end) return false;
  if (resolvedIso === null || resolvedIso === undefined || resolvedIso === "") return true;
  const resolved = parseTimestamp(resolvedIso);
  if (!resolved.ok) return true;
  return resolved.utcMs >= start;
}

export function cohortJql(projectKey, window, timeZone) {
  const query = jqlQueryWindow(window, timeZone);
  return `project = "${projectKey}" AND created < "${query.end}" AND (resolved IS EMPTY OR resolved >= "${query.start}") ORDER BY created ASC, key ASC`;
}
