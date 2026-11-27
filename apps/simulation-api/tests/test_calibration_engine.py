from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.calibration.catalog import request_for_fixture
from app.calibration.contracts import CalibrationRequest
from app.calibration.histories import (
    approved_capacity_and_service,
    default_mapping,
    generate_history,
)
from app.calibration.snapshot import content_fingerprint, validate_snapshot_structure
from app.calibration.workflow import calibrate
from app.domain.models import OperationalModel


def test_generated_golden_snapshot_matches_os_schema(repository_root: Path) -> None:
    schema = json.loads((repository_root / "contracts" / "operational-snapshot.schema.json").read_text())  # noqa: E501
    snapshot = generate_history("golden", 7)
    Draft202012Validator(schema).validate(snapshot)
    assert validate_snapshot_structure(snapshot) is None
    assert snapshot["contentFingerprint"] == content_fingerprint(snapshot)


def test_fingerprint_mismatch_is_rejected() -> None:
    snapshot = generate_history("golden", 1)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    request.snapshot_fingerprint = "a" * 64
    artifact = calibrate(snapshot, request)
    assert artifact.failure_class == "invalid_evidence"
    assert artifact.constructed_model is None


def test_status_residence_is_not_service_time() -> None:
    snapshot = generate_history("partial", 3)
    request = request_for_fixture("cg3-partially-observable", snapshot, approve=False)
    artifact = calibrate(snapshot, request)
    service = [item for item in artifact.parameter_estimates if "processing_time" in item.parameter_id]  # noqa: E501
    assert service
    assert all(item.identifiability_status in {"not_identifiable", "insufficient_evidence"} for item in service)  # noqa: E501
    assert all(item.estimation_method.startswith("refused") for item in service)
    assert artifact.readiness_status == "assumptions_required"


def test_capacity_is_not_assignee_count() -> None:
    snapshot = generate_history("partial", 4)
    request = request_for_fixture("cg3-partially-observable", snapshot, approve=False)
    artifact = calibrate(snapshot, request)
    capacity = [item for item in artifact.parameter_estimates if item.parameter_id.startswith("resource.")]  # noqa: E501
    assert capacity
    assert all(item.estimation_method == "refused_assignee_count" for item in capacity)


def test_unapproved_assumptions_block_construction() -> None:
    snapshot = generate_history("partial", 5)
    payload = request_for_fixture("cg3-partially-observable", snapshot, approve=True).model_dump(by_alias=True)  # noqa: E501
    for item in payload["assumptionSet"]:
        item["approvalStatus"] = "proposed"
    artifact = calibrate(snapshot, CalibrationRequest.model_validate(payload))
    assert artifact.readiness_status == "assumptions_required"
    assert artifact.constructed_model is None


def test_assumption_revision_changes_identity() -> None:
    snapshot = generate_history("partial", 6)
    first = request_for_fixture("cg3-partially-observable", snapshot, approve=True)
    second_payload = first.model_dump(by_alias=True)
    second_payload["assumptionSet"][0]["proposedValue"] = 9
    second_payload["assumptionSet"][0]["revision"] = 2
    a = calibrate(snapshot, first)
    b = calibrate(snapshot, CalibrationRequest.model_validate(second_payload))
    assert a.content_identity != b.content_identity
    assert a.model_fingerprint != b.model_fingerprint


def test_unmapped_statuses_require_review() -> None:
    snapshot = generate_history("golden", 8)
    request = CalibrationRequest.model_validate(
        {
            "snapshotReference": "x",
            "snapshotFingerprint": snapshot["contentFingerprint"],
            "operationalMapping": {"reviewed": False, "statuses": []},
        }
    )
    artifact = calibrate(snapshot, request)
    assert artifact.readiness_status == "mapping_required"


def test_rework_is_not_inferred_from_reopening() -> None:
    snapshot = generate_history("golden", 9)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    rework = next(item for item in artifact.parameter_estimates if item.parameter_id == "rework.probability")  # noqa: E501
    assert rework.identifiability_status == "not_identifiable"
    assert rework.value is None


def test_golden_recovers_arrival_rate() -> None:
    snapshot = generate_history("golden", 11)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    arrival = next(item for item in artifact.parameter_estimates if item.parameter_id == "arrival.mean_interarrival_time")  # noqa: E501
    assert arrival.value is not None
    assert abs(float(arrival.value) - 30.0) / 30.0 < 0.35
    assert artifact.constructed_model is not None
    OperationalModel.model_validate(artifact.constructed_model.model_dump(by_alias=True))


def test_holdout_uses_training_only_and_records_thresholds() -> None:
    snapshot = generate_history("observable", 12)
    request = request_for_fixture("cg3-fully-observable", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.validation_report is not None
    assert artifact.validation_report.thresholds_recorded_before_evaluation.arrival_volume_relative == 0.15  # noqa: E501
    train_end = artifact.training_configuration["end"]
    hold_start = artifact.validation_configuration["start"]
    assert hold_start >= train_end
    assert artifact.provenance["holdoutLeakage"] == "training_only_estimation"


def test_misspecified_topology_is_refused() -> None:
    snapshot = generate_history("misspecified", 13)
    request = request_for_fixture("cg3-misspecified", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.failure_class == "unsupported_topology"
    assert artifact.validation_report is None


def test_noisy_incomplete_extraction_is_refused() -> None:
    snapshot = generate_history("noisy", 14)
    request = request_for_fixture("cg3-noisy", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.failure_class == "insufficient_evidence"
    assert artifact.constructed_model is None


def test_unsupported_schema_is_rejected() -> None:
    snapshot = generate_history("golden", 15)
    snapshot["schemaVersion"] = "os.0.0.1"
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.failure_class == "invalid_evidence"


def test_default_mapping_helper() -> None:
    mapping = default_mapping(reviewed=True)
    assert mapping["reviewed"] is True
    assert len(approved_capacity_and_service()) == 4
