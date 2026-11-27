from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, cast

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
        created = parse_utc(case.get("createdAt"))
        if created is None or case.get("createdAtInvalid"):
            continue
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
    return "unknown"  # noqa: E501


def poisson_rate_interval(count: int, exposure_minutes: float) -> UncertaintyInterval:
    rate = count / exposure_minutes
    se = math.sqrt(count) / exposure_minutes if count else 0.0
    return UncertaintyInterval(
        kind="poisson_rate_normal",
        lower=max(0.0, rate - 1.96 * se),
        upper=rate + 1.96 * se,
        unit="cases_per_minute",
        notes="Normal approximation to a Poisson count. Not an assumption range.",
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
    }
    if exposure <= 0:
        raise EstimationError("invalid_evidence", "Training exposure time must be positive.")
    if len(stamps) < config.min_arrival_sample:
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
        ),
        {
            **diagnostics,
            "rate_per_minute": rate,
            "poisson_adequate": adequate,
            "split_ratio": split_ratio,
            "split_shift": split_shift,
        },
    )


def _worklog_samples(
    snapshot: dict[str, Any],
    start: datetime,
    end: datetime,
    mapping: OperationalMapping,
) -> tuple[dict[str, list[float]], int, int]:
    samples: dict[str, list[float]] = {"triage": [], "resolution": []}
    overlap = 0
    censored = 0
    by_case: dict[str, list[dict[str, Any]]] = {}
    for interval in snapshot.get("intervals") or []:
        if interval.get("intervalType") != "recorded_work":
            continue
        begin = parse_utc(interval.get("startAt"))
        if begin is None or not (start <= begin < end):
            continue
        if interval.get("complete") is not True or interval.get("censoring") != "none":
            censored += 1
            continue
        duration = interval.get("durationMinutes")
        if not isinstance(duration, int | float) or duration < 0:
            continue
        by_case.setdefault(str(interval["caseId"]), []).append(interval)
        stage_id = "triage"
        status_ref = interval.get("statusReference")
        mapped = stage_of(status_ref, mapping) if status_ref else None
        if mapped:
            stage_id = mapped
        elif len(samples["triage"]) > len(samples["resolution"]):
            stage_id = "resolution"
        samples[stage_id].append(float(duration))
    for intervals in by_case.values():
        ordered = sorted(intervals, key=lambda item: parse_utc(item.get("startAt")) or start)
        for left, right in zip(ordered, ordered[1:], strict=False):
            left_end = parse_utc(left.get("endAt"))
            right_start = parse_utc(right.get("startAt"))
            if left_end and right_start and right_start < left_end:
                overlap += 1
    return samples, overlap, censored


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
    diagnostics = {"status_residence_count": len(residence)}
    samples, overlap, censored = _worklog_samples(snapshot, start, end, mapping)
    diagnostics.update({"worklog_overlap_count": overlap, "censored_duration_excluded": censored})
    estimates: list[ParameterEstimate] = []
    for stage_id, path in (
        ("triage", "stages[triage].processingTime.mean"),
        ("resolution", "stages[resolution].processingTime.mean"),
    ):
        assumption_id = f"{stage_id}.processing_time.mean"
        values = samples[stage_id]
        if request.estimation_configuration.treat_worklogs_as_processing and overlap == 0:
            if len(values) >= request.estimation_configuration.min_duration_sample:
                mean = sum(values) / len(values)
                estimates.append(
                    ParameterEstimate(
                        parameter_id=assumption_id,
                        target_model_path=path,
                        parameter_type="exponential_mean_minutes",
                        value=mean,
                        unit="minutes",
                        estimation_method="worklog_mean_exponential",
                        evidence_class=_origin(snapshot),
                        identifiability_status="identifiable",
                        sample_size=len(values),
                        uncertainty=UncertaintyInterval(
                            kind="sample_sd",
                            lower=max(1e-6, mean * 0.5),
                            upper=mean * 1.5,
                            unit="minutes",
                            notes="Heuristic scale around the sample mean; not a bootstrap CI.",
                        ),
                        source_references=["intervals.recorded_work"],
                        limitations=[
                            "Worklogs are not automatically active processing time.",
                            "Censored or overlapping worklogs were excluded.",
                        ],
                    )
                )
                continue
        approved = _approved(request, assumption_id)
        if approved is not None:
            value = float(approved.proposed_value)
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
                identifiability_status="not_identifiable"
                if residence
                else "insufficient_evidence",
                sample_size=len(values),
                source_references=["intervals.status_residence"],
                limitations=["Status residence includes waiting and inactivity and is not service time."],  # noqa: E501
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
            estimates.append(
                ParameterEstimate(
                    parameter_id=assumption_id,
                    target_model_path=path,
                    parameter_type="capacity",
                    value=int(float(approved.proposed_value)),
                    unit="servers",
                    estimation_method="approved_assumption",
                    evidence_class="assumed",
                    identifiability_status="assumption_required",
                    sample_size=len(assignees),
                    assumptions=[assumption_id],
                    limitations=["Distinct assignees are not staffing capacity."],
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
    if triage_total >= request.estimation_configuration.min_routing_sample:
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
            )
        )
    elif triage_total == 0:
        estimates.append(
            ParameterEstimate(
                parameter_id="routing.triage_to_resolution",
                target_model_path="routes[triage-success].options",
                parameter_type="probability",
                value=1.0,
                unit="probability",
                estimation_method="template_default_single_path",
                evidence_class="derived",
                identifiability_status="partially_identifiable",
                sample_size=0,
                limitations=["Linear template path used because no competing processing route was observed."],  # noqa: E501
            )
        )
    else:
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
        )
    ]


def split_windows(
    snapshot: dict[str, Any],
    request: CalibrationRequest,
) -> tuple[datetime, datetime, datetime, datetime]:
    if request.training_window and request.validation_window:
        train_start, train_end = window_bounds(request.training_window.start, request.training_window.end)  # noqa: E501
        hold_start, hold_end = window_bounds(
            request.validation_window.start, request.validation_window.end
        )
        if hold_start < train_end:
            raise EstimationError("invalid_evidence", "Holdout must start at or after the training end.")  # noqa: E501
        return train_start, train_end, hold_start, hold_end
    window = snapshot.get("observationWindow") or {}
    start, end = window_bounds(str(window.get("start")), str(window.get("end")))
    created = [parse_utc(case.get("createdAt")) for case in snapshot.get("cases") or []]
    stamps = sorted(stamp for stamp in created if stamp is not None and start <= stamp < end)
    if len(stamps) < 4:
        raise EstimationError("insufficient_evidence", "Too few created timestamps to form a temporal split.")  # noqa: E501
    cut_index = max(1, min(len(stamps) - 1, int(len(stamps) * request.estimation_configuration.training_fraction)))  # noqa: E501
    cut = stamps[cut_index]
    if cut <= start or cut >= end:
        cut = start + timedelta(minutes=minutes_between(start, end) * request.estimation_configuration.training_fraction)  # noqa: E501
    return start, cut, cut, end
