from __future__ import annotations

from app.calibration.catalog import request_for_fixture
from app.calibration.contracts import CalibrationRequest, OperationalMapping, StatusMapping
from app.calibration.histories import generate_history
from app.calibration.mapping import MappingError, validate_mapping
from app.calibration.snapshot import content_fingerprint, validate_snapshot_structure
from app.calibration.workflow import calibrate


def test_fractional_capacity_is_rejected() -> None:
    snapshot = generate_history("partial", 81)
    payload = request_for_fixture("cg3-partially-observable", snapshot, approve=True).model_dump(by_alias=True)  # noqa: E501
    for item in payload["assumptionSet"]:
        if item["assumptionId"] == "resource.triage-team.capacity":
            item["proposedValue"] = 2.7
    artifact = calibrate(snapshot, CalibrationRequest.model_validate(payload))
    assert artifact.constructed_model is None
    assert artifact.failure_class == "contract_validation_failure"


def test_string_numeric_assumption_is_rejected() -> None:
    snapshot = generate_history("partial", 82)
    payload = request_for_fixture("cg3-partially-observable", snapshot, approve=True).model_dump(by_alias=True)  # noqa: E501
    payload["assumptionSet"][0]["proposedValue"] = "8"
    artifact = calibrate(snapshot, CalibrationRequest.model_validate(payload))
    assert artifact.constructed_model is None
    assert artifact.failure_class == "contract_validation_failure"


def test_assumption_id_must_match_affected_parameter() -> None:
    snapshot = generate_history("partial", 83)
    payload = request_for_fixture("cg3-partially-observable", snapshot, approve=True).model_dump(by_alias=True)  # noqa: E501
    payload["assumptionSet"][0]["affectedParameter"] = "resource.triage-team.capacity"
    artifact = calibrate(snapshot, CalibrationRequest.model_validate(payload))
    assert artifact.failure_class == "contract_validation_failure"


def test_unknown_approved_parameter_is_rejected() -> None:
    snapshot = generate_history("partial", 84)
    payload = request_for_fixture("cg3-partially-observable", snapshot, approve=True).model_dump(by_alias=True)  # noqa: E501
    payload["assumptionSet"].append(
        {
            **payload["assumptionSet"][0],
            "assumptionId": "gamma.shape",
            "affectedParameter": "gamma.shape",
            "unit": "minutes",
        }
    )
    artifact = calibrate(snapshot, CalibrationRequest.model_validate(payload))
    assert artifact.failure_class == "unsupported_parameter"


def test_assumption_based_model_policy_is_enforced() -> None:
    snapshot = generate_history("partial", 85)
    payload = request_for_fixture("cg3-partially-observable", snapshot, approve=True).model_dump(by_alias=True)  # noqa: E501
    payload["estimationConfiguration"]["allowAssumptionBasedModel"] = False
    artifact = calibrate(snapshot, CalibrationRequest.model_validate(payload))
    assert artifact.readiness_status == "assumptions_required"
    assert artifact.constructed_model is None


def test_processing_stage_is_not_inferred_from_list_order() -> None:
    snapshot = generate_history("golden", 86)
    mapping = OperationalMapping(
        reviewed=True,
        statuses=[
            StatusMapping(status_id="s-open", role="queue", reviewed=True),
            StatusMapping(status_id="s-triage", role="processing", reviewed=True),
            StatusMapping(status_id="s-res", role="processing", reviewed=True),
            StatusMapping(status_id="s-done", role="completed", reviewed=True),
        ],
    )
    try:
        validate_mapping(snapshot, mapping)
        raise AssertionError("missing stage identifiers must not be inferred")
    except MappingError as error:
        assert error.code in {"unsupported_topology", "mapping_required"}


def test_duplicate_status_mapping_is_rejected() -> None:
    snapshot = generate_history("golden", 87)
    mapping = OperationalMapping(
        reviewed=True,
        statuses=[
            StatusMapping(status_id="s-open", role="queue", reviewed=True),
            StatusMapping(status_id="s-open", role="completed", reviewed=True),
            StatusMapping(status_id="s-triage", role="processing", stage_id="triage", reviewed=True),  # noqa: E501
            StatusMapping(status_id="s-res", role="processing", stage_id="resolution", reviewed=True),  # noqa: E501
            StatusMapping(status_id="s-done", role="completed", reviewed=True),
        ],
    )
    try:
        validate_mapping(snapshot, mapping)
        raise AssertionError("duplicate mappings must fail")
    except MappingError:
        pass


def test_incomplete_snapshot_is_not_complete_evidence() -> None:
    snapshot = generate_history("golden", 88)
    snapshot["completenessStatus"] = "partial"
    snapshot["extraction"]["complete"] = True
    snapshot["contentFingerprint"] = content_fingerprint(snapshot)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.constructed_model is None
    assert validate_snapshot_structure(generate_history("golden", 88)) is None
