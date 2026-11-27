from __future__ import annotations

import time
from datetime import datetime
from typing import Any, cast, get_args

from app.calibration.assumptions import AssumptionError, validate_assumptions
from app.calibration.construct import ConstructionError, construct_model, model_fingerprint
from app.calibration.contracts import (
    ENGINE_VERSION,
    MAPPING_VERSION,
    MATERIAL_PARAMETERS,
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
from app.calibration.holdout import evaluate_holdout, historical_open_at, iso
from app.calibration.mapping import MappingError, validate_mapping
from app.calibration.snapshot import (
    content_fingerprint,
    sha256_canonical,
    validate_snapshot_structure,
)


def _content_identity(request: CalibrationRequest, model_fp: str | None) -> str:
    return sha256_canonical(
        {
            "snapshot": request.snapshot_fingerprint,
            "mapping": request.operational_mapping.model_dump(by_alias=True),
            "assumptions": [item.model_dump(by_alias=True) for item in request.assumption_set],
            "template": TEMPLATE_ID,
            "engine": ENGINE_VERSION,
            "estimation": request.estimation_configuration.model_dump(by_alias=True),
            "thresholds": request.validation_thresholds.model_dump(by_alias=True),
            "budget": request.execution_budget.model_dump(by_alias=True),
            "trainingWindow": None
            if request.training_window is None
            else request.training_window.model_dump(by_alias=True),
            "validationWindow": None
            if request.validation_window is None
            else request.validation_window.model_dump(by_alias=True),
            "model": model_fp,
        }
    )


def _execution_identity(
    model_fp: str,
    train_start: datetime,
    train_end: datetime,
    hold_start: datetime,
    hold_end: datetime,
    seeds: list[int],
    item_count: int,
    request: CalibrationRequest,
) -> str:
    return sha256_canonical(
        {
            "model": model_fp,
            "training": {"start": iso(train_start), "end": iso(train_end)},
            "holdout": {"start": iso(hold_start), "end": iso(hold_end)},
            "simulationSeeds": seeds,
            "itemCount": item_count,
            "engine": ENGINE_VERSION,
            "budget": request.execution_budget.model_dump(by_alias=True),
            "thresholds": request.validation_thresholds.model_dump(by_alias=True),
            "calibrationSeed": request.random_seed,
        }
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
    identity = _content_identity(request, None)
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
        execution_identity=None,
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


def calibrate(snapshot: dict[str, Any], request: CalibrationRequest) -> CalibrationArtifact:
    started = time.perf_counter()
    timings = ExecutionMetadata(fixture_seed=request.random_seed)
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
    if snapshot.get("completenessStatus") != "complete":
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            "insufficient_evidence",
            "Incomplete snapshots are not accepted as complete calibration evidence.",
            [],
            diagnostics,
            timings,
        )
    emit_calibration("calibration.snapshot.validated", {"accepted": True})
    try:
        validate_assumptions(request)
    except AssumptionError as error:
        failure: FailureClass = (
            "unsupported_parameter" if error.code == "unsupported_parameter" else "contract_validation_failure"  # noqa: E501
        )
        if error.code == "missing_assumptions":
            failure = "missing_assumptions"
        readiness: ReadinessStatus = (
            "assumptions_required" if error.code == "missing_assumptions" else "insufficient_evidence"  # noqa: E501
        )
        return _blocked(request, snapshot, readiness, failure, error.message, [], diagnostics, timings)  # noqa: E501
    try:
        mapping_info = validate_mapping(snapshot, request.operational_mapping)
    except MappingError as error:
        diagnostics.unmapped_statuses = list(error.details.get("unmapped") or [])
        readiness = "mapping_required" if error.code == "mapping_required" else "insufficient_evidence"  # noqa: E501
        failure = "unsupported_topology" if error.code == "unsupported_topology" else "insufficient_evidence"  # noqa: E501
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
    try:
        arrival, arrival_diag = estimate_arrivals(snapshot, train_start, train_end, request)
        service, service_diag = estimate_service_times(
            snapshot, train_start, train_end, request, request.operational_mapping
        )
        capacity = estimate_capacity(snapshot, request)
        routing, unsupported = estimate_routing(
            snapshot, train_start, train_end, request.operational_mapping, request
        )
        mix = mix_estimates(snapshot, train_start, train_end)
    except (EstimationError, AssumptionError) as error:
        timings.estimation_ms = (time.perf_counter() - estimation_started) * 1000
        code = str(getattr(error, "code", "invalid_evidence"))
        allowed = get_args(FailureClass)
        failure_code = cast(FailureClass, code if code in allowed else "invalid_evidence")
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            failure_code,
            str(error),
            [],
            diagnostics,
            timings,
        )
    estimates = [arrival, *service, *capacity, *routing, *mix]
    timings.estimation_ms = (time.perf_counter() - estimation_started) * 1000
    diagnostics.arrival_dispersion = arrival_diag.get("dispersion")
    diagnostics.weekday_concentration = arrival_diag.get("weekday_concentration")
    diagnostics.homogeneous_poisson_adequate = arrival_diag.get("poisson_adequate")
    diagnostics.worklog_overlap_count = int(service_diag.get("worklog_overlap_count") or 0)
    diagnostics.worklog_unattributed_count = int(service_diag.get("worklog_unattributed_count") or 0)  # noqa: E501
    diagnostics.worklog_duplicate_count = int(service_diag.get("worklog_duplicate_count") or 0)
    diagnostics.worklog_invalid_count = int(service_diag.get("worklog_invalid_count") or 0)
    diagnostics.censored_duration_excluded = int(service_diag.get("censored_duration_excluded") or 0)  # noqa: E501
    diagnostics.unsupported_transitions = unsupported
    backlog, unknown_backlog = historical_open_at(
        snapshot, hold_start, request.operational_mapping
    )
    diagnostics.initial_backlog_at_holdout = backlog
    diagnostics.unknown_backlog_at_holdout = unknown_backlog
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
        if item.consumed_by_model and item.parameter_id in MATERIAL_PARAMETERS and item.value is None  # noqa: E501
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
        model = construct_model(estimates, request.random_seed)
    except ConstructionError as error:
        timings.construction_ms = (time.perf_counter() - construct_started) * 1000
        construct_failure: FailureClass = (
            "unsupported_parameter"
            if error.code == "unsupported_parameter"
            else "missing_assumptions"
            if error.code == "missing_assumptions"
            else "contract_validation_failure"
        )
        return _blocked(
            request,
            snapshot,
            "insufficient_evidence",
            construct_failure,
            error.message,
            estimates,
            diagnostics,
            timings,
        )
    fingerprint = model_fingerprint(model)
    timings.construction_ms = (time.perf_counter() - construct_started) * 1000
    emit_calibration("calibration.model.constructed", {"modelFingerprint": fingerprint[:16]})
    identity = _content_identity(request, fingerprint)
    sim_started = time.perf_counter()
    try:
        report, item_count, seeds, excluded = evaluate_holdout(
            snapshot,
            model,
            train_start,
            train_end,
            hold_start,
            hold_end,
            request.random_seed,
            request.validation_thresholds,
            request.execution_budget.max_items,
            request.operational_mapping,
            request.execution_budget.max_replications,
            backlog,
            unknown_backlog,
        )
    except Exception:  # noqa: BLE001
        timings.simulation_ms = (time.perf_counter() - sim_started) * 1000
        diagnostics.notes.append("execution_failure")
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
    timings.replication_count = report.replication_count
    timings.requested_replications = report.requested_replications
    timings.excluded_replications = excluded
    timings.simulation_seeds = seeds
    timings.arrivals_truncated = report.arrivals_truncated
    timings.total_ms = (time.perf_counter() - started) * 1000
    if model.sources[0].item_count != 1:
        return _blocked(
            request,
            snapshot,
            "validation_failed",
            "execution_failure",
            "Canonical constructed model was mutated during validation.",
            estimates,
            diagnostics,
            timings,
        )
    execution_identity = _execution_identity(
        fingerprint, train_start, train_end, hold_start, hold_end, seeds, item_count, request
    )
    if report.overall_outcome == "passed_for_defined_scope":
        readiness = "validated_for_defined_scope"
    elif report.overall_outcome == "failed":
        readiness = "validation_failed"
    else:
        readiness = "model_constructed"
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
        execution_identity=execution_identity,
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
            "unknownBacklog": diagnostics.unknown_backlog_at_holdout,
            "itemCount": item_count,
            "simulationSeeds": seeds,
            "validationClass": report.validation_class,
            "arrivalsTruncated": report.arrivals_truncated,
        },
        diagnostics=diagnostics,
        readiness_status=readiness,
        provenance={
            "schemaVersion": SCHEMA_VERSION,
            "engineVersion": ENGINE_VERSION,
            "snapshotReference": request.snapshot_reference,
            "evidenceClass": (snapshot.get("provenance") or {}).get("evidenceClass"),
            "holdoutLeakage": "training_only_estimation",
            "modelIdentityNote": "Model identity excludes execution itemCount and simulation seeds.",  # noqa: E501
        },
        execution_metadata=timings,
        validation_report=report,
        content_identity=identity,
        failure_class="historical_validation_failure" if readiness == "validation_failed" else None,
        blocked_reason=None,
    )
