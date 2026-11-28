from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, cast

from app.calibration.assumptions import finite_number
from app.calibration.contracts import (
    AssumptionRecord,
    CalibrationRequest,
    EvidenceClass,
    IdentifiabilityStatus,
    OperationalMapping,
    ParameterEstimate,
    UncertaintyInterval,
)
from app.calibration.mapping import role_of, stage_of
from app.calibration.snapshot import minutes_between, parse_utc

T_CRIT_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
}


class EstimationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def window_bounds(start: str, end: str) -> tuple[datetime, datetime]:
    begin = parse_utc(start)
    finish = parse_utc(end)
    if begin is None or finish is None or finish <= begin:
        raise EstimationError("invalid_evidence", "Observation windows must be valid UTC intervals.")  # noqa: E501
    return begin, finish


def cases_created_in(snapshot: dict[str, Any], start: datetime, end: datetime) -> list[dict[str, Any]]:  # noqa: E501
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in snapshot.get("cases") or []:
        if case.get("createdAtInvalid"):
            raise EstimationError(
                "invalid_evidence",
                "Malformed created timestamps cannot be dropped from the arrival population.",
            )
        created = parse_utc(case.get("createdAt"))
        if created is None:
            raise EstimationError("invalid_evidence", "Every case in the estimation population needs a valid createdAt.")  # noqa: E501
        case_id = str(case.get("caseId"))
        if case_id in seen:
            continue
        if start <= created < end:
            seen.add(case_id)
            selected.append(case)
    return selected


def _assumption(request: CalibrationRequest, assumption_id: str) -> AssumptionRecord | None:
    matches = [item for item in request.assumption_set if item.assumption_id == assumption_id]
    return matches[-1] if matches else None


def _approved(request: CalibrationRequest, assumption_id: str) -> AssumptionRecord | None:
    item = _assumption(request, assumption_id)
    if item is None or item.approval_status != "approved":
        return None
    return item


def _origin(snapshot: dict[str, Any]) -> EvidenceClass:
    evidence = (snapshot.get("provenance") or {}).get("evidenceClass")
    if evidence in {"observed", "derived", "assumed", "synthetic", "unknown"}:
        return cast(EvidenceClass, evidence)
    return "unknown"


def poisson_rate_interval(count: int, exposure_minutes: float) -> UncertaintyInterval:
    rate = count / exposure_minutes
    se = math.sqrt(count) / exposure_minutes if count else 0.0
    notes = "Normal approximation to a Poisson count. Not an assumption range."
    if count < 10:
        notes += " Finite-sample coverage is poor below about 10 events."
    return UncertaintyInterval(
        kind="poisson_rate_normal",
        lower=max(0.0, rate - 1.96 * se),
        upper=rate + 1.96 * se,
        unit="cases_per_minute",
        notes=notes,
    )


def sample_mean_t_interval(values: list[float]) -> UncertaintyInterval | None:
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    se = math.sqrt(variance / n)
    tcrit = T_CRIT_95.get(n - 1, 1.96)
    return UncertaintyInterval(
        kind="sample_mean_t",
        lower=max(1e-6, mean - tcrit * se),
        upper=mean + tcrit * se,
        unit="minutes",
        notes="Student t 95% interval for the mean of complete processing episodes. Not a CI for mixed-origin evidence.",  # noqa: E501
    )


def weekday_concentration(created: list[datetime]) -> float | None:
    if len(created) < 8:
        return None
    counts = Counter(stamp.weekday() for stamp in created)
    values = list(counts.values())
    return max(values) / max(min(values), 1)


def day_dispersion(created: list[datetime], start: datetime, end: datetime) -> float | None:
    if len(created) < 8:
        return None
    days = max(1, math.ceil(minutes_between(start, end) / 1440))
    buckets = [0] * days
    for stamp in created:
        index = min(days - 1, int(minutes_between(start, stamp) // 1440))
        buckets[index] += 1
    mean = sum(buckets) / days
    if mean <= 0:
        return None
    variance = sum((value - mean) ** 2 for value in buckets) / days
    return variance / mean


def estimate_arrivals(
    snapshot: dict[str, Any],
    start: datetime,
    end: datetime,
    request: CalibrationRequest,
) -> tuple[ParameterEstimate, dict[str, Any]]:
    created_cases = cases_created_in(snapshot, start, end)
    created_at = [parse_utc(case["createdAt"]) for case in created_cases]
    stamps = [stamp for stamp in created_at if stamp is not None]
    exposure = minutes_between(start, end)
    config = request.estimation_configuration
    diagnostics = {
        "sample_size": len(stamps),
        "exposure_minutes": exposure,
        "dispersion": day_dispersion(stamps, start, end),
        "weekday_concentration": weekday_concentration(stamps),
        "partial_day_exposure": exposure % 1440 != 0,
    }
    if exposure <= 0:
        raise EstimationError("invalid_evidence", "Training exposure time must be positive.")
    if len(stamps) < config.min_arrival_sample:
        approved = _approved(request, "arrival.mean_interarrival_time")
        if approved is not None:
            value = finite_number(approved.proposed_value, label="arrival.mean_interarrival_time")
            return (
                ParameterEstimate(
                    parameter_id="arrival.mean_interarrival_time",
                    target_model_path="sources[0].arrival.meanInterarrivalTime",
                    parameter_type="mean_interarrival_minutes",
                    value=value,
                    unit="minutes",
                    estimation_method="approved_assumption",
                    evidence_class="assumed",
                    identifiability_status="assumption_required",
                    sample_size=len(stamps),
                    source_references=["cases.createdAt"],
                    limitations=["Arrival rate is an approved assumption because the training sample is below the configured minimum."],  # noqa: E501
                    origin="approved_assumption",
                ),
                diagnostics,
            )
        return (
            ParameterEstimate(
                parameter_id="arrival.mean_interarrival_time",
                target_model_path="sources[0].arrival.meanInterarrivalTime",
                parameter_type="mean_interarrival_minutes",
                value=None,
                unit="minutes",
                estimation_method="homogeneous_poisson_mle",
                evidence_class=_origin(snapshot),
                identifiability_status="insufficient_evidence",
                sample_size=len(stamps),
                source_references=["cases.createdAt"],
                limitations=["Training arrival sample is below the configured minimum."],
                origin="empirical_estimate",
            ),
            diagnostics,
        )
    rate = len(stamps) / exposure
    mean_ia = exposure / len(stamps)
    half = start + (end - start) / 2
    first = sum(start <= stamp < half for stamp in stamps)
    second = sum(half <= stamp < end for stamp in stamps)
    split_ratio = max(first, 1) / max(second, 1)
    first_rate = first / max(minutes_between(start, half), 1)
    second_rate = second / max(minutes_between(half, end), 1)
    mean_rate = (first_rate + second_rate) / 2
    split_shift = abs(first_rate - second_rate) / mean_rate if mean_rate else 0.0
    adequate = True
    if diagnostics["dispersion"] is not None and diagnostics["dispersion"] > 6:
        adequate = False
    if split_shift > 0.75:
        adequate = False
    ident: IdentifiabilityStatus = "identifiable" if adequate else "partially_identifiable"
    return (
        ParameterEstimate(
            parameter_id="arrival.mean_interarrival_time",
            target_model_path="sources[0].arrival.meanInterarrivalTime",
            parameter_type="mean_interarrival_minutes",
            value=mean_ia,
            unit="minutes",
            estimation_method="homogeneous_poisson_mle",
            evidence_class=_origin(snapshot),
            identifiability_status=ident,
            sample_size=len(stamps),
            uncertainty=poisson_rate_interval(len(stamps), exposure),
            source_references=["cases.createdAt"],
            limitations=[
                "Calendar minutes are not resource availability.",
                "Homogeneous Poisson is rejected when training demand is strongly split or overdispersed.",  # noqa: E501
            ],
            origin="empirical_estimate",
        ),
        {
            **diagnostics,
            "rate_per_minute": rate,
            "poisson_adequate": adequate,
            "split_ratio": split_ratio,
            "split_shift": split_shift,
        },
    )


def _interval_key(interval: dict[str, Any]) -> tuple[Any, ...]:
    return (
        interval.get("caseId"),
        interval.get("startAt"),
        interval.get("endAt"),
        interval.get("durationMinutes"),
        interval.get("statusReference"),
    )


def _worklog_samples(
    snapshot: dict[str, Any],
    start: datetime,
    end: datetime,
    mapping: OperationalMapping,
) -> tuple[dict[str, list[float]], dict[str, int]]:
    samples: dict[str, list[float]] = {"triage": [], "resolution": []}
    counts = {
        "overlap": 0,
        "censored": 0,
        "unattributed": 0,
        "duplicates": 0,
        "invalid": 0,
        "boundary_crossing": 0,
        "holdout_only": 0,
        "outside_training": 0,
    }
    seen: set[tuple[Any, ...]] = set()
    attributed: list[tuple[str, str, datetime, datetime, float]] = []
    for interval in snapshot.get("intervals") or []:
        if interval.get("intervalType") != "recorded_work":
            continue
        begin = parse_utc(interval.get("startAt"))
        finish = parse_utc(interval.get("endAt"))
        duration = interval.get("durationMinutes")
        if begin is None or (interval.get("endAt") and finish is None):
            counts["invalid"] += 1
            continue
        if finish is not None and begin is not None and finish < begin:
            counts["invalid"] += 1
            continue
        if not isinstance(duration, int | float) or isinstance(duration, bool) or duration <= 0:
            counts["invalid"] += 1
            continue
        if finish is not None and abs(float(duration) - minutes_between(begin, finish)) > 1 / 60:
            counts["invalid"] += 1
            continue
        key = _interval_key(interval)
        if key in seen:
            counts["duplicates"] += 1
            continue
        seen.add(key)
        if begin >= end:
            counts["holdout_only"] += 1
            continue
        if finish is not None and finish > end:
            counts["boundary_crossing"] += 1
            counts["censored"] += 1
            continue
        if begin < start:
            counts["outside_training"] += 1
            counts["censored"] += 1
            continue
        if interval.get("complete") is not True or interval.get("censoring") != "none" or finish is None:  # noqa: E501
            counts["censored"] += 1
            continue
        status_ref = interval.get("statusReference")
        mapped = stage_of(status_ref, mapping) if status_ref else None
        if mapped not in samples:
            counts["unattributed"] += 1
            continue
        attributed.append((str(interval["caseId"]), mapped, begin, finish, float(duration)))
    attributed.sort(key=lambda item: (item[0], item[1], item[2]))
    episodes: list[tuple[str, str, datetime, datetime, float]] = []
    for item in attributed:
        if not episodes:
            episodes.append(item)
            continue
        case_id, stage_id, begin, finish, duration = item
        prev_case, prev_stage, prev_begin, prev_finish, prev_duration = episodes[-1]
        if case_id == prev_case and stage_id == prev_stage and begin < prev_finish:
            counts["overlap"] += 1
            merged_end = max(prev_finish, finish)
            episodes[-1] = (case_id, stage_id, prev_begin, merged_end, minutes_between(prev_begin, merged_end))  # noqa: E501
            continue
        if case_id == prev_case and stage_id == prev_stage and begin == prev_finish:
            episodes[-1] = (
                case_id,
                stage_id,
                prev_begin,
                finish,
                prev_duration + duration,
            )
            continue
        episodes.append(item)
    for _case_id, stage_id, _begin, _finish, duration in episodes:
        samples[stage_id].append(duration)
    counts["episodes"] = len(episodes)
    return samples, counts


def _worklogs_complete(snapshot: dict[str, Any], request: CalibrationRequest) -> bool:
    extraction = snapshot.get("extraction") or {}
    if extraction.get("worklogCompleteness") == "complete" and extraction.get("worklogCapability") == "retrieved":  # noqa: E501
        return True
    approved = _approved(request, "worklog.completeness")
    return approved is not None


def estimate_service_times(
    snapshot: dict[str, Any],
    start: datetime,
    end: datetime,
    request: CalibrationRequest,
    mapping: OperationalMapping,
) -> tuple[list[ParameterEstimate], dict[str, Any]]:
    residence = [
        interval
        for interval in snapshot.get("intervals") or []
        if interval.get("intervalType") == "status_residence"
    ]
    diagnostics: dict[str, Any] = {"status_residence_count": len(residence)}
    samples, counts = _worklog_samples(snapshot, start, end, mapping)
    diagnostics.update(
        {
            "worklog_overlap_count": counts["overlap"],
            "censored_duration_excluded": counts["censored"],
            "worklog_unattributed_count": counts["unattributed"],
            "worklog_duplicate_count": counts["duplicates"],
            "worklog_invalid_count": counts["invalid"],
            "worklog_boundary_crossing": counts["boundary_crossing"],
            "worklog_holdout_only": counts["holdout_only"],
        }
    )
    usable = (
        request.estimation_configuration.treat_worklogs_as_processing
        and _worklogs_complete(snapshot, request)
        and counts["overlap"] == 0
        and counts["invalid"] == 0
    )
    estimates: list[ParameterEstimate] = []
    for stage_id, path in (
        ("triage", "stages[triage].processingTime.mean"),
        ("resolution", "stages[resolution].processingTime.mean"),
    ):
        assumption_id = f"{stage_id}.processing_time.mean"
        values = samples[stage_id]
        if usable and len(values) >= request.estimation_configuration.min_duration_sample:
            mean = sum(values) / len(values)
            estimates.append(
                ParameterEstimate(
                    parameter_id=assumption_id,
                    target_model_path=path,
                    parameter_type="exponential_mean_minutes",
                    value=mean,
                    unit="minutes",
                    estimation_method="worklog_episode_mean_exponential",
                    evidence_class=_origin(snapshot),
                    identifiability_status="identifiable",
                    sample_size=len(values),
                    uncertainty=sample_mean_t_interval(values),
                    source_references=["intervals.recorded_work"],
                    limitations=[
                        "Only attributed, complete, in-window processing episodes are used.",
                        "A Boolean worklog-usage flag is not itself attribution or completeness.",
                    ],
                    origin="empirical_estimate",
                )
            )
            continue
        approved = _approved(request, assumption_id)
        if approved is not None:
            value = finite_number(approved.proposed_value, label=assumption_id)
            estimates.append(
                ParameterEstimate(
                    parameter_id=assumption_id,
                    target_model_path=path,
                    parameter_type="exponential_mean_minutes",
                    value=value,
                    unit="minutes",
                    estimation_method="approved_assumption",
                    evidence_class="assumed",
                    identifiability_status="assumption_required",
                    sample_size=len(values),
                    uncertainty=UncertaintyInterval(
                        kind="assumption_range",
                        lower=float(approved.lower_bound) if approved.lower_bound is not None else value,  # noqa: E501
                        upper=float(approved.upper_bound) if approved.upper_bound is not None else value,  # noqa: E501
                        unit="minutes",
                        notes="Plausible assumption range, not a statistical confidence interval.",
                    ),
                    source_references=[],
                    assumptions=[assumption_id],
                    limitations=["Status residence was not used as processing time."],
                    origin="approved_assumption",
                )
            )
            continue
        estimates.append(
            ParameterEstimate(
                parameter_id=assumption_id,
                target_model_path=path,
                parameter_type="exponential_mean_minutes",
                value=None,
                unit="minutes",
                estimation_method="refused_status_residence",
                evidence_class=_origin(snapshot),
                identifiability_status="not_identifiable" if residence else "insufficient_evidence",
                sample_size=len(values),
                source_references=["intervals.status_residence"],
                limitations=["Status residence includes waiting and inactivity and is not service time."],  # noqa: E501
                origin="empirical_estimate",
            )
        )
    return estimates, diagnostics


def estimate_capacity(snapshot: dict[str, Any], request: CalibrationRequest) -> list[ParameterEstimate]:  # noqa: E501
    assignees = {
        case.get("assigneeReference")
        for case in snapshot.get("cases") or []
        if case.get("assigneeReference")
    }
    estimates: list[ParameterEstimate] = []
    for pool_id, path in (
        ("triage-team", "resourcePools[triage-team].capacity"),
        ("resolution-team", "resourcePools[resolution-team].capacity"),
    ):
        assumption_id = f"resource.{pool_id}.capacity"
        approved = _approved(request, assumption_id)
        if approved is not None:
            value = finite_number(approved.proposed_value, label=assumption_id)
            if value != int(value):
                raise EstimationError(
                    "contract_validation_failure",
                    f"{assumption_id} staffing capacity must be a whole number of servers.",
                )
            estimates.append(
                ParameterEstimate(
                    parameter_id=assumption_id,
                    target_model_path=path,
                    parameter_type="capacity",
                    value=int(value),
                    unit="servers",
                    estimation_method="approved_assumption",
                    evidence_class="assumed",
                    identifiability_status="assumption_required",
                    sample_size=len(assignees),
                    assumptions=[assumption_id],
                    limitations=["Distinct assignees are not staffing capacity."],
                    origin="approved_assumption",
                )
            )
            continue
        estimates.append(
            ParameterEstimate(
                parameter_id=assumption_id,
                target_model_path=path,
                parameter_type="capacity",
                value=None,
                unit="servers",
                estimation_method="refused_assignee_count",
                evidence_class=_origin(snapshot),
                identifiability_status="not_identifiable",
                sample_size=len(assignees),
                source_references=["cases.assigneeReference"],
                limitations=["Assignee counts are not licensed or scheduled capacity."],
                origin="empirical_estimate",
            )
        )
    return estimates


def estimate_routing(
    snapshot: dict[str, Any],
    start: datetime,
    end: datetime,
    mapping: OperationalMapping,
    request: CalibrationRequest,
) -> tuple[list[ParameterEstimate], list[str]]:
    unsupported: list[str] = []
    from_triage: Counter[str] = Counter()
    from_resolution: Counter[str] = Counter()
    for event in snapshot.get("events") or []:
        if event.get("eventType") != "status_changed":
            continue
        occurred = parse_utc(event.get("occurredAt"))
        if occurred is None or not (start <= occurred < end):
            continue
        previous_role = role_of(event.get("previousValue"), mapping)
        next_role = role_of(event.get("newValue"), mapping)
        if previous_role == "processing" and next_role in {"processing", "completed", "queue", "review"}:  # noqa: E501
            origin = stage_of(event.get("previousValue"), mapping) or "triage"
            target = stage_of(event.get("newValue"), mapping) if next_role == "processing" else next_role  # noqa: E501
            key = f"{origin}->{target}"
            if origin == "triage" and target in {"resolution", "completed"}:
                from_triage[str(target)] += 1
            elif origin == "resolution" and target in {"completed", "triage"}:
                from_resolution[str(target)] += 1
            elif origin == "triage" and next_role == "processing" and target == "triage":
                continue
            else:
                unsupported.append(key)
        elif previous_role == "processing" and next_role not in {None, "excluded"}:
            unsupported.append(f"{event.get('previousValue')}->{event.get('newValue')}")
    estimates: list[ParameterEstimate] = []
    triage_total = sum(from_triage.values())
    competing = set(from_triage) - {"resolution"}
    if unsupported:
        estimates.append(
            ParameterEstimate(
                parameter_id="routing.triage_to_resolution",
                target_model_path="routes[triage-success].options",
                parameter_type="probability",
                value=None,
                unit="probability",
                estimation_method="empirical_transition_share",
                evidence_class=_origin(snapshot),
                identifiability_status="not_identifiable",
                sample_size=triage_total,
                source_references=["events.status_changed"],
                limitations=["Unknown competing routes are not assigned probability zero."],
                origin="empirical_estimate",
            )
        )
    elif triage_total >= request.estimation_configuration.min_routing_sample:
        to_resolution = from_triage.get("resolution", 0) / triage_total
        estimates.append(
            ParameterEstimate(
                parameter_id="routing.triage_to_resolution",
                target_model_path="routes[triage-success].options",
                parameter_type="probability",
                value=to_resolution,
                unit="probability",
                estimation_method="empirical_transition_share",
                evidence_class=_origin(snapshot),
                identifiability_status="identifiable",
                sample_size=triage_total,
                source_references=["events.status_changed"],
                limitations=["Unknown routes are not assigned probability zero."],
                origin="empirical_estimate",
            )
        )
    elif competing:
        estimates.append(
            ParameterEstimate(
                parameter_id="routing.triage_to_resolution",
                target_model_path="routes[triage-success].options",
                parameter_type="probability",
                value=None,
                unit="probability",
                estimation_method="empirical_transition_share",
                evidence_class=_origin(snapshot),
                identifiability_status="insufficient_evidence",
                sample_size=triage_total,
                limitations=["Sparse routing samples are not smoothed to hide uncertainty."],
                origin="empirical_estimate",
            )
        )
    else:
        estimates.append(
            ParameterEstimate(
                parameter_id="routing.triage_to_resolution",
                target_model_path="routes[triage-success].options",
                parameter_type="probability",
                value=1.0,
                unit="probability",
                estimation_method="structural_linear_template",
                evidence_class="derived",
                identifiability_status="partially_identifiable",
                sample_size=triage_total,
                limitations=[
                    "Linear template constraint: triage success routes to resolution.",
                    "This is not an empirical probability and is not a missing-data default.",
                ],
                origin="structural_constraint",
            )
        )
    reopen_events = [
        event
        for event in snapshot.get("events") or []
        if event.get("eventType") == "reopened" and parse_utc(event.get("occurredAt"))
    ]
    estimates.append(
        ParameterEstimate(
            parameter_id="rework.probability",
            target_model_path="stages[resolution].failure.probability",
            parameter_type="probability",
            value=None,
            unit="probability",
            estimation_method="refused_reopen_as_rework",
            evidence_class=_origin(snapshot),
            identifiability_status="not_identifiable",
            sample_size=len(reopen_events),
            limitations=["Reopening is not treated as processing failure or rework."],
            consumed_by_model=False,
            origin="diagnostic_only",
            validation_status="excluded",
        )
    )
    return estimates, unsupported


def mix_estimates(snapshot: dict[str, Any], start: datetime, end: datetime) -> list[ParameterEstimate]:  # noqa: E501
    created = cases_created_in(snapshot, start, end)
    types = Counter(str(case.get("requestTypeReference") or "unclassified") for case in created)
    total = sum(types.values())
    return [
        ParameterEstimate(
            parameter_id="demand.mix",
            target_model_path="sources[*].mix",
            parameter_type="categorical_share",
            value=None,
            unit="share",
            estimation_method="empirical_counts",
            evidence_class=_origin(snapshot),
            identifiability_status="identifiable" if total else "insufficient_evidence",
            sample_size=total,
            source_references=["cases.requestTypeReference"],
            limitations=["The supported template uses a single arrival class; mix is diagnostic only."],  # noqa: E501
            consumed_by_model=False,
            origin="diagnostic_only",
            validation_status="excluded",
        )
    ]


def observation_bounds(snapshot: dict[str, Any]) -> tuple[datetime, datetime]:
    window = snapshot.get("observationWindow") or {}
    return window_bounds(str(window.get("start")), str(window.get("end")))


def split_windows(
    snapshot: dict[str, Any],
    request: CalibrationRequest,
) -> tuple[datetime, datetime, datetime, datetime]:
    obs_start, obs_end = observation_bounds(snapshot)
    if request.training_window and request.validation_window:
        train_start, train_end = window_bounds(request.training_window.start, request.training_window.end)  # noqa: E501
        hold_start, hold_end = window_bounds(
            request.validation_window.start, request.validation_window.end
        )
    else:
        span = obs_end - obs_start
        cut = obs_start + timedelta(seconds=span.total_seconds() * request.estimation_configuration.training_fraction)  # noqa: E501
        train_start, train_end, hold_start, hold_end = obs_start, cut, cut, obs_end
    if train_start < obs_start or hold_end > obs_end or train_end > obs_end or hold_start < obs_start:  # noqa: E501
        raise EstimationError("invalid_evidence", "Training and holdout windows must lie inside the snapshot observation window.")  # noqa: E501
    if hold_start < train_end:
        raise EstimationError("invalid_evidence", "Holdout must start at or after the training end.")  # noqa: E501
    if train_end <= train_start or hold_end <= hold_start:
        raise EstimationError("invalid_evidence", "Training and holdout windows must be non-empty.")  # noqa: E501
    return train_start, train_end, hold_start, hold_end
