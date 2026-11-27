from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from app.calibration.construct import ConstructionError, construct_model, model_fingerprint
from app.calibration.contracts import (
    ENGINE_VERSION,
    MAPPING_VERSION,
    SCHEMA_VERSION,
    TEMPLATE_ID,
    CalibrationArtifact,
    CalibrationDiagnostics,
    CalibrationRequest,
    ExecutionMetadata,
    FailureClass,
    ParameterEstimate,
    ReadinessStatus,
)
from app.calibration.estimate import (
    EstimationError,
    cases_created_in,
    estimate_arrivals,
    estimate_capacity,
    estimate_routing,
    estimate_service_times,
    mix_estimates,
    split_windows,
)
from app.calibration.events import emit_calibration
from app.calibration.holdout import evaluate_holdout, iso
from app.calibration.mapping import MappingError, validate_mapping
from app.calibration.snapshot import (
    content_fingerprint,
    parse_utc,
    sha256_canonical,
    validate_snapshot_structure,
)


def _blocked(
    request: CalibrationRequest,
    snapshot: dict[str, Any],
    readiness: ReadinessStatus,
    failure: FailureClass,
    reason: str,
    estimates: list[ParameterEstimate],
    diagnostics: CalibrationDiagnostics,
    timings: ExecutionMetadata,
    mapping_version: str = MAPPING_VERSION,
) -> CalibrationArtifact:
    identity = sha256_canonical(
        {
            "snapshot": request.snapshot_fingerprint,
            "mapping": request.operational_mapping.model_dump(by_alias=True),
            "assumptions": [item.model_dump(by_alias=True) for item in request.assumption_set],
            "template": TEMPLATE_ID,
            "engine": ENGINE_VERSION,
        }
    )
    emit_calibration(
        "calibration.blocked",
        {
            "calibrationId": identity[:16],
            "snapshotFingerprint": request.snapshot_fingerprint[:16],
            "reason": failure,
        },
    )
    return CalibrationArtifact(
        calibration_id=f"cal_{identity[:24]}",
        source_snapshot_fingerprint=request.snapshot_fingerprint,
        model_template_version=TEMPLATE_ID,
        mapping_version=mapping_version,
        parameter_estimates=estimates,
        assumptions=request.assumption_set,
        constructed_model=None,
        model_fingerprint=None,
        training_configuration={},
        validation_configuration={},
        diagnostics=diagnostics,
        readiness_status=readiness,
        provenance={
            "schemaVersion": SCHEMA_VERSION,
            "engineVersion": ENGINE_VERSION,
            "snapshotReference": request.snapshot_reference,
            "evidenceClass": (snapshot.get("provenance") or {}).get("evidenceClass"),
        },
        execution_metadata=timings,
        validation_report=None,
        content_identity=identity,
        failure_class=failure,
        blocked_reason=reason,
    )


def _backlog(snapshot: dict[str, Any], cutoff: datetime) -> int:
    count = 0
    for case in snapshot.get("cases") or []:
        created = parse_utc(case.get("createdAt"))
        resolved = parse_utc(case.get("resolvedAt"))
        if created is None or created >= cutoff:
            continue
        if resolved is None or resolved >= cutoff:
            count += 1
    return count


def calibrate(snapshot: dict[str, Any], request: CalibrationRequest) -> CalibrationArtifact:
    started = time.perf_counter()
    timings = ExecutionMetadata()
    diagnostics = CalibrationDiagnostics()
    emit_calibration(
        "calibration.requested",
        {"snapshotFingerprint": request.snapshot_fingerprint[:16], "template": TEMPLATE_ID},
    )
    structural = validate_snapshot_structure(snapshot)
    timings.snapshot_validation_ms = (time.perf_counter() - started) * 1000
    if structural:
        emit_calibration("calibration.snapshot.validated", {"accepted": False})
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "invalid_evidence",
            structural,
            [],
            diagnostics,
            timings,
        )
    computed = content_fingerprint(snapshot)
    if computed != request.snapshot_fingerprint or computed != snapshot.get("contentFingerprint"):
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "invalid_evidence",
            "Snapshot fingerprint does not match immutable content identity.",
            [],
            diagnostics,
            timings,
        )
    if snapshot.get("extraction", {}).get("complete") is False:
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "insufficient_evidence",
            "Partial extraction cannot be treated as a complete calibration input.",
            [],
            diagnostics,
            timings,
        )
    emit_calibration("calibration.snapshot.validated", {"accepted": True})
    try:
        mapping_info = validate_mapping(snapshot, request.operational_mapping)
    except MappingError as error:
        diagnostics.unmapped_statuses = list(error.details.get("unmapped") or [])
        readiness: ReadinessStatus = (
            "mapping_required" if error.code == "mapping_required" else "insufficient_evidence"
        )
        failure: FailureClass = (
            "unsupported_topology" if error.code == "unsupported_topology" else "insufficient_evidence"  # noqa: E501
        )
        emit_calibration("calibration.mapping.validated", {"accepted": False, "reason": error.code})
        return _blocked(request, snapshot, readiness, failure, error.message, [], diagnostics, timings)  # noqa: E501
    emit_calibration("calibration.mapping.validated", {"accepted": True})
    try:
        train_start, train_end, hold_start, hold_end = split_windows(snapshot, request)
    except EstimationError as error:
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "insufficient_evidence",
            error.message,
            [],
            diagnostics,
            timings,
        )
    estimation_started = time.perf_counter()
    arrival, arrival_diag = estimate_arrivals(snapshot, train_start, train_end, request)
    service, service_diag = estimate_service_times(
        snapshot, train_start, train_end, request, request.operational_mapping
    )
    capacity = estimate_capacity(snapshot, request)
    routing, unsupported = estimate_routing(
        snapshot, train_start, train_end, request.operational_mapping, request
    )
    mix = mix_estimates(snapshot, train_start, train_end)
    estimates = [arrival, *service, *capacity, *routing, *mix]
    timings.estimation_ms = (time.perf_counter() - estimation_started) * 1000
    diagnostics.arrival_dispersion = arrival_diag.get("dispersion")
    diagnostics.weekday_concentration = arrival_diag.get("weekday_concentration")
    diagnostics.homogeneous_poisson_adequate = arrival_diag.get("poisson_adequate")
    diagnostics.worklog_overlap_count = int(service_diag.get("worklog_overlap_count") or 0)
    diagnostics.censored_duration_excluded = int(service_diag.get("censored_duration_excluded") or 0)  # noqa: E501
    diagnostics.unsupported_transitions = unsupported
    diagnostics.initial_backlog_at_holdout = _backlog(snapshot, hold_start)
    diagnostics.unmapped_statuses = list(mapping_info.get("unmapped") or [])
    emit_calibration(
        "calibration.eligibility.completed",
        {"arrival": arrival.identifiability_status, "sampleSize": arrival.sample_size},
    )
    if unsupported:
        diagnostics.notes.append("Unsupported observed transitions were not assigned probability zero.")  # noqa: E501
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "unsupported_topology",
            "Observed transitions are not representable by the supported template.",
            estimates,
            diagnostics,
            timings,
        )
    if arrival_diag.get("poisson_adequate") is False:
        diagnostics.notes.append("Homogeneous Poisson is inadequate for the training arrivals.")
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "statistical_estimation_failure",
            "Training arrivals are inconsistent with a homogeneous Poisson model.",
            estimates,
            diagnostics,
            timings,
        )
    missing = [
        item.parameter_id
        for item in estimates
        if item.value is None
        and item.parameter_id
        in {
            "arrival.mean_interarrival_time",
            "triage.processing_time.mean",
            "resolution.processing_time.mean",
            "resource.triage-team.capacity",
            "resource.resolution-team.capacity",
        }
    ]
    if missing:
        emit_calibration("calibration.assumption.required", {"parameters": ",".join(missing)})
        return _blocked(
            request,
            snapshot,
            "assumptions_required",
            "missing_assumptions",
            "Material parameters remain unapproved: " + ", ".join(missing),
            estimates,
            diagnostics,
            timings,
        )
    if any(item.approval_status == "approved" for item in request.assumption_set):
        emit_calibration("calibration.assumption.approved", {"count": len(request.assumption_set)})
    construct_started = time.perf_counter()
    try:
        model = construct_model(estimates, request.random_seed, item_count=8)
    except ConstructionError as error:
        timings.construction_ms = (time.perf_counter() - construct_started) * 1000
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "contract_validation_failure",
            error.message,
            estimates,
            diagnostics,
            timings,
        )
    fingerprint = model_fingerprint(model)
    timings.construction_ms = (time.perf_counter() - construct_started) * 1000
    emit_calibration("calibration.model.constructed", {"modelFingerprint": fingerprint[:16]})
    identity = sha256_canonical(
        {
            "snapshot": request.snapshot_fingerprint,
            "mapping": request.operational_mapping.model_dump(by_alias=True),
            "assumptions": [item.model_dump(by_alias=True) for item in request.assumption_set],
            "template": TEMPLATE_ID,
            "engine": ENGINE_VERSION,
            "model": fingerprint,
        }
    )
    sim_started = time.perf_counter()
    try:
        report, _result, item_count = evaluate_holdout(
            snapshot,
            model,
            train_start,
            train_end,
            hold_start,
            hold_end,
            request.random_seed,
            request.validation_thresholds,
            request.execution_budget.max_items,
        )
    except Exception as error:  # noqa: BLE001
        timings.simulation_ms = (time.perf_counter() - sim_started) * 1000
        diagnostics.notes.append(type(error).__name__)
        return _blocked(
            request,
            snapshot,
            "validation_failed",
            "execution_failure",
            "Baseline simulation failed for the constructed model.",
            estimates,
            diagnostics,
            timings,
        )
    timings.simulation_ms = (time.perf_counter() - sim_started) * 1000
    timings.validation_ms = timings.simulation_ms
    timings.item_count = item_count
    timings.total_ms = (time.perf_counter() - started) * 1000
    model.sources[0].item_count = item_count
    readiness = (
        "validated_for_defined_scope"
        if report.overall_outcome == "passed_for_defined_scope"
        else "validation_failed"
        if report.overall_outcome == "failed"
        else "model_constructed"
    )
    emit_calibration(
        "calibration.validation.completed",
        {"status": report.overall_outcome, "duration": round(timings.total_ms, 1)},
    )
    return CalibrationArtifact(
        calibration_id=f"cal_{identity[:24]}",
        source_snapshot_fingerprint=request.snapshot_fingerprint,
        model_template_version=TEMPLATE_ID,
        mapping_version=MAPPING_VERSION,
        parameter_estimates=estimates,
        assumptions=request.assumption_set,
        constructed_model=model,
        model_fingerprint=fingerprint,
        training_configuration={
            "start": iso(train_start),
            "end": iso(train_end),
            "createdInTraining": len(cases_created_in(snapshot, train_start, train_end)),
        },
        validation_configuration={
            "start": iso(hold_start),
            "end": iso(hold_end),
            "mode": "generative",
            "initialBacklog": diagnostics.initial_backlog_at_holdout,
        },
        diagnostics=diagnostics,
        readiness_status=readiness,
        provenance={
            "schemaVersion": SCHEMA_VERSION,
            "engineVersion": ENGINE_VERSION,
            "snapshotReference": request.snapshot_reference,
            "evidenceClass": (snapshot.get("provenance") or {}).get("evidenceClass"),
            "holdoutLeakage": "training_only_estimation",
        },
        execution_metadata=timings,
        validation_report=report,
        content_identity=identity,
        failure_class="historical_validation_failure" if readiness == "validation_failed" else None,
        blocked_reason=None,
    )
