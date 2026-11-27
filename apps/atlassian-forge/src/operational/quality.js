function ratio(numerator, denominator) {
  if (!denominator) return null;
  return numerator / denominator;
}

function quality(metricId, definition, numerator, denominator, status, explanation, consequence, recommendedNextAction) {
  return {
    metricId,
    definition,
    numerator,
    denominator,
    value: ratio(numerator, denominator),
    status,
    explanation,
    consequence,
    recommendedNextAction,
  };
}

function percentile(sorted, p) {
  if (sorted.length === 0) return null;
  const index = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[Math.max(0, index)];
}

function countBy(items, keyFn) {
  const counts = {};
  for (const item of items) {
    const key = keyFn(item) ?? "unclassified";
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return Object.entries(counts)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, count]) => ({ key, count }));
}

export function assessDataQuality(normalized, extraction, window) {
  const { cases, events, intervals } = normalized;
  const n = cases.length;
  const validCreated = cases.filter((item) => item.createdAt && !item.createdAtInvalid).length;
  const invalidCreated = cases.filter((item) => item.createdAtInvalid).length;
  const completeLifecycle = cases.filter((item) => item.lifecycleCompleteness === "complete").length;
  const withStatusHistory = new Set(events.filter((item) => item.eventType === "status_changed").map((item) => item.caseId)).size;
  const withWorklog = new Set(events.filter((item) => item.eventType === "worklog_recorded").map((item) => item.caseId)).size;
  const withSla = new Set(events.filter((item) => item.eventType === "sla_cycle_observed").map((item) => item.caseId)).size;
  const classifiedType = cases.filter((item) => item.requestTypeReference).length;
  const classifiedStatus = cases.filter((item) => item.currentStatusReference).length;
  const uniqueIds = new Set(cases.map((item) => item.caseId)).size;
  const uniqueEvents = new Set(events.map((item) => item.eventId)).size;
  const negative = intervals.filter((item) => item.intervalType === "unknown" && item.durationMinutes === null && item.startAt && item.endAt).length;
  const extractedOk = extraction.complete && extraction.truncatedReason === null;

  const completeness = quality(
    "completeness",
    "Share of cases with a valid created timestamp.",
    validCreated,
    n || null,
    n === 0 ? "not_applicable" : validCreated === n ? "pass" : validCreated === 0 ? "fail" : "warning",
    n === 0 ? "No cases were observed." : `${validCreated} of ${n} cases have a valid created timestamp.`,
    "Missing created timestamps prevent arrival and lifetime measurement.",
    "Inspect source created fields; do not impute zeros.",
  );
  const validity = quality(
    "validity",
    "Share of cases without invalid timestamps.",
    n - invalidCreated,
    n || null,
    invalidCreated > 0 ? "fail" : n === 0 ? "not_applicable" : "pass",
    invalidCreated > 0 ? `${invalidCreated} cases have invalid created timestamps.` : "No invalid created timestamps were detected.",
    "Invalid timestamps are excluded from temporal metrics.",
    "Reject or repair source records; do not coerce clocks.",
  );
  const consistency = quality(
    "consistency",
    "Cases whose events do not precede creation.",
    n - cases.filter((item) =>
      events.some((event) => {
        if (event.caseId !== item.caseId || event.eventType === "case_created" || !event.occurredAt || !item.createdAt) return false;
        return Date.parse(event.occurredAt) < Date.parse(item.createdAt);
      }),
    ).length,
    n || null,
    negative > 0 ? "warning" : "pass",
    "Related timestamps were compared without rewriting source history.",
    "Inconsistent histories produce unknown intervals.",
    "Keep unknown intervals visible in the snapshot.",
  );
  const uniqueness = quality(
    "uniqueness",
    "Deduplicated case identifiers relative to raw case count.",
    uniqueIds,
    n || null,
    uniqueIds !== n ? "fail" : uniqueEvents !== events.length ? "warning" : n === 0 ? "not_applicable" : "pass",
    "Duplicate identities are removed during normalization.",
    "Duplicates would inflate demand counts.",
    "Keep deterministic dedupe keys.",
  );
  const temporal = quality(
    "temporal_coverage",
    "Configured observation window length in days.",
    window.windowDays ?? null,
    90,
    "pass",
    `Window is ${window.start} to ${window.end} (${window.convention}).`,
    "Metrics apply only inside this window.",
    "Re-import with a longer window if coverage is insufficient.",
  );
  const lifecycle = quality(
    "lifecycle_coverage",
    "Share of cases with reconstructable status history.",
    withStatusHistory,
    n || null,
    n === 0 ? "not_applicable" : completeLifecycle === n ? "pass" : withStatusHistory === 0 ? "fail" : "warning",
    `${completeLifecycle} cases have complete histories; ${withStatusHistory} have at least one status change.`,
    "Missing changelogs prevent status residence measurement.",
    "Do not treat current status as a full history.",
  );
  const worklogStatus =
    extraction.worklogCapability === "forbidden"
      ? "unknown"
      : extraction.worklogCapability === "not_requested"
        ? "not_applicable"
        : n === 0
          ? "not_applicable"
          : withWorklog === 0
            ? "warning"
            : "pass";
  const worklogs = quality(
    "worklog_coverage",
    "Share of cases with at least one recorded worklog.",
    withWorklog,
    n || null,
    worklogStatus,
    `Worklog capability is ${extraction.worklogCapability}.`,
    "Recorded work is not active processing time.",
    "Leave work duration unknown when worklogs are absent.",
  );
  const slaStatus =
    extraction.slaCapability === "forbidden" || extraction.slaCapability === "unavailable"
      ? "unknown"
      : extraction.slaCapability === "not_requested"
        ? "not_applicable"
        : n === 0
          ? "not_applicable"
          : withSla === 0
            ? "warning"
            : "pass";
  const sla = quality(
    "sla_coverage",
    "Share of cases with an observed SLA cycle.",
    withSla,
    n || null,
    slaStatus,
    `SLA capability is ${extraction.slaCapability}.`,
    "SLA elapsed time uses the source calendar and is not interchangeable with residence time.",
    "Do not substitute status duration for SLA elapsed time.",
  );
  const classification = quality(
    "classification_coverage",
    "Share of cases with both a request type and a current status reference.",
    cases.filter((item) => item.requestTypeReference && item.currentStatusReference).length,
    n || null,
    n === 0 ? "not_applicable" : classifiedType === n && classifiedStatus === n ? "pass" : "warning",
    `${classifiedType} cases have request types; ${classifiedStatus} have current statuses. Issue type is not treated as request type.`,
    "Unclassified cases cannot be used as typed demand mix without assumptions.",
    "Keep unclassified records explicit.",
  );
  const representativeness = quality(
    "representativeness",
    "Whether retrieved pages are a statistical sample of operations. Extraction completeness is not representativeness.",
    extractedOk ? 1 : 0,
    1,
    extractedOk ? "warning" : "fail",
    extractedOk
      ? n === 0
        ? "Extraction finished and observed zero cases. Completeness of retrieval is not representativeness."
        : "All requested pages were retrieved. That does not establish that the cohort represents future or unobserved work."
      : `Extraction was incomplete (${extraction.truncatedReason ?? "interrupted"}).`,
    "A finished page walk is not a sampling design.",
    "Keep calibration blocked until population coverage is argued separately.",
  );
  const authorization = quality(
    "authorization_coverage",
    "Whether records were retrieved with user-context project authorization.",
    extraction.authorized === false ? 0 : 1,
    1,
    extraction.authorized === false ? "fail" : "pass",
    extraction.authorized === false ? "The caller was not authorized for this project." : "Records were constrained to the trusted project context.",
    "Unauthorized data must not be shown as an operational snapshot.",
    "Keep asUser() and reject browser project substitution.",
  );

  return [
    completeness,
    validity,
    consistency,
    uniqueness,
    temporal,
    lifecycle,
    worklogs,
    sla,
    classification,
    representativeness,
    authorization,
  ];
}

export function descriptiveEvidence(normalized, window, provenanceBase) {
  const { cases, events, intervals } = normalized;
  const windowLabel = `${window.start}/${window.end}`;
  const derived = {
    ...provenanceBase,
    evidenceClass: "derived",
    derivationMethod: "deterministic-descriptive-os.1.0.0",
  };
  const resolved = cases.filter((item) => item.observationStatus === "resolved" && item.createdAt && item.resolvedAt);
  const lifetimes = resolved
    .map((item) => intervals.find((interval) => interval.caseId === item.caseId && interval.intervalType === "elapsed_lifetime" && interval.complete))
    .filter(Boolean)
    .map((item) => item.durationMinutes)
    .filter((value) => value !== null)
    .sort((a, b) => a - b);
  const residences = intervals
    .filter((item) => item.intervalType === "status_residence" && item.durationMinutes !== null)
    .map((item) => item.durationMinutes)
    .sort((a, b) => a - b);
  const work = intervals
    .filter((item) => item.intervalType === "recorded_work" && item.durationMinutes !== null)
    .map((item) => item.durationMinutes)
    .sort((a, b) => a - b);
  const arrivals = cases.filter((item) => item.createdAt && Date.parse(item.createdAt) >= Date.parse(window.start) && Date.parse(item.createdAt) < Date.parse(window.end)).length;
  const openAtEnd = cases.filter((item) => {
    if (!item.createdAt || Date.parse(item.createdAt) >= Date.parse(window.end)) return false;
    if (item.observationStatus === "open" || item.observationStatus === "reopened") return true;
    if (item.observationStatus === "resolved" && item.resolvedAt) return Date.parse(item.resolvedAt) >= Date.parse(window.end);
    return false;
  }).length;
  const transitions = events.filter((item) => item.eventType === "status_changed").length;
  const assigneeTransitions = events.filter((item) => item.eventType === "assigned" || item.eventType === "reassigned").length;
  const slaEvents = events.filter((item) => item.eventType === "sla_cycle_observed");
  const slaBreached = slaEvents.filter((item) => item.previousValue === "breached").length;
  const slaKnown = slaEvents.filter((item) => item.previousValue === "breached" || item.previousValue === "not_breached").length;
  const reopeningEvents = events.filter((item) => item.eventType === "reopened").length;
  const everReopened = new Set(events.filter((item) => item.eventType === "reopened").map((item) => item.caseId)).size;
  const currentlyReopened = cases.filter((item) => item.observationStatus === "reopened").length;
  const worklogCases = new Set(events.filter((item) => item.eventType === "worklog_recorded").map((item) => item.caseId)).size;
  const residenceAll = intervals.filter((item) => item.intervalType === "status_residence").length;
  const workAll = intervals.filter((item) => item.intervalType === "recorded_work").length;

  function boundedShare(numerator, denominator) {
    if (!denominator) return null;
    const value = numerator / denominator;
    if (value < 0 || value > 1) return null;
    return value;
  }

  function metric(metricId, definition, value, unit, population, sampleSize, excluded, limitations, coverage) {
    return {
      metricId,
      definition,
      value,
      unit,
      population,
      sampleSize,
      observationWindow: windowLabel,
      excludedRecords: excluded,
      coverage: coverage === undefined ? boundedShare(sampleSize, cases.length) : coverage,
      provenance: derived,
      interpretationLimitations: limitations,
    };
  }

  return [
    metric("observed_case_count", "Number of normalized cases in the snapshot.", cases.length, "cases", "all snapshot cases", cases.length, 0, "Count is not staffing capacity."),
    metric("arrivals_in_window", "Cases whose created timestamp falls inside the observation window.", arrivals, "cases", "created in window", arrivals, cases.length - arrivals, "Excludes cases already open at window start."),
    metric("request_type_distribution", "Counts by request type reference.", countBy(cases, (item) => item.requestTypeReference), "counts", "all snapshot cases", cases.length, 0, "Missing request types are grouped as unclassified. Issue type is a different concept."),
    metric("priority_distribution", "Counts by source priority reference.", countBy(cases, (item) => item.priorityReference), "counts", "all snapshot cases", cases.length, 0, "Priority names are source labels, not simulated classes."),
    metric("resolution_count", "Cases whose latest observed resolution stands at window end.", resolved.length, "cases", "resolved with timestamps", resolved.length, cases.length - resolved.length, "Reopened cases are excluded from this count."),
    metric("reopen_count", "Cases currently reopened at the observation cutoff.", currentlyReopened, "cases", "currently reopened cases", currentlyReopened, cases.length - currentlyReopened, "This is not the count of reopening events or of cases ever reopened."),
    metric("cases_ever_reopened", "Distinct cases with at least one reopened event.", everReopened, "cases", "cases with a reopen event", everReopened, cases.length - everReopened, "Ever-reopened is not the same as currently reopened."),
    metric("reopening_event_count", "Number of reopened events.", reopeningEvents, "events", "reopened events", reopeningEvents, 0, "Event counts do not use the case count as a coverage denominator.", 1),
    metric(
      "cycle_time_minutes",
      "Elapsed lifetime from created to resolved for complete resolved cases.",
      { sampleSize: lifetimes.length, p50: percentile(lifetimes, 50), p90: percentile(lifetimes, 90), mean: lifetimes.length ? lifetimes.reduce((a, b) => a + b, 0) / lifetimes.length : null },
      "minutes",
      "resolved cases with complete elapsed lifetime",
      lifetimes.length,
      cases.length - lifetimes.length,
      "Elapsed lifetime is not active processing time and not SLA elapsed time.",
    ),
    metric(
      "status_residence_minutes",
      "Observed residence in source statuses, including waiting and inactivity.",
      { sampleSize: residences.length, p50: percentile(residences, 50), p90: percentile(residences, 90) },
      "minutes",
      "status residence intervals with a duration",
      residences.length,
      residenceAll - residences.length,
      "A long residence does not prove a processing bottleneck.",
    ),
    metric("status_transition_count", "Number of observed status_changed events.", transitions, "events", "status changelog items", transitions, 0, "Transitions are not handoffs unless assignment also changed. Coverage is not case-based.", 1),
    metric("open_cases_at_window_end", "Cases created before window end and not resolved before window end.", openAtEnd, "cases", "open at cutoff", openAtEnd, cases.length - openAtEnd, "Right-censored; not a steady-state WIP theorem result."),
    metric(
      "worklog_coverage_share",
      "Share of cases with recorded worklogs.",
      boundedShare(worklogCases, cases.length),
      "share",
      "all snapshot cases",
      worklogCases,
      cases.length - worklogCases,
      "Recorded work duration is not utilization. Missing worklogs are not zero.",
      boundedShare(worklogCases, cases.length),
    ),
    metric(
      "recorded_work_minutes",
      "Distribution of recorded worklog durations.",
      work.length ? { sampleSize: work.length, p50: percentile(work, 50), mean: work.reduce((a, b) => a + b, 0) / work.length } : null,
      "minutes",
      "worklog intervals with duration",
      work.length,
      workAll - work.length,
      "Missing worklogs are not zero work.",
      boundedShare(work.length, workAll),
    ),
    metric("sla_cycle_count", "Observed SLA cycle records, including earlier completed cycles and ongoing cycles.", slaEvents.length, "cycles", "retrieved SLA records", slaEvents.length, 0, "SLA completion uses the source calendar; missing SLA is not a met target.", 1),
    metric("sla_breach_count", "SLA cycles flagged breached by the source.", slaBreached, "cycles", "SLA cycles with a known breach flag", slaBreached, slaEvents.length - slaKnown, "Unknown breach flags are not coerced to false.", boundedShare(slaKnown, slaEvents.length)),
    metric("assignee_transition_count", "Assigned and reassigned events.", assigneeTransitions, "events", "assignee changelog items", assigneeTransitions, 0, "Unique assignees are not licensed agent capacity.", 1),
  ];
}

export function classifyReadiness(qualityResults, extraction, caseCount) {
  if (qualityResults.some((item) => item.metricId === "authorization_coverage" && item.status === "fail")) {
    return { completenessStatus: "invalid", readiness: "invalid" };
  }
  if (qualityResults.some((item) => item.metricId === "validity" && item.status === "fail") && caseCount > 0) {
    return { completenessStatus: "invalid", readiness: "invalid" };
  }
  if (!extraction.complete) {
    return { completenessStatus: "partial", readiness: "partial" };
  }
  if (caseCount === 0) {
    return { completenessStatus: "empty", readiness: "insufficient_for_calibration" };
  }
  const lifecycle = qualityResults.find((item) => item.metricId === "lifecycle_coverage");
  if (lifecycle?.status === "fail") {
    return { completenessStatus: "complete", readiness: "insufficient_for_calibration" };
  }
  if (lifecycle?.status === "warning") {
    return { completenessStatus: "complete", readiness: "potentially_suitable_for_calibration_assessment" };
  }
  return { completenessStatus: "complete", readiness: "potentially_suitable_for_calibration_assessment" };
}
