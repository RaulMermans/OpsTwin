from __future__ import annotations

from app.calibration.catalog import request_for_fixture
from app.calibration.contracts import CalibrationRequest
from app.calibration.histories import generate_history
from app.calibration.workflow import calibrate


def test_unknown_values_are_not_zero() -> None:
    snapshot = generate_history("partial", 41)
    artifact = calibrate(snapshot, request_for_fixture("cg3-partially-observable", snapshot, approve=False))  # noqa: E501
    rework = next(item for item in artifact.parameter_estimates if item.parameter_id == "rework.probability")  # noqa: E501
    assert rework.value is None


def test_mixed_origin_is_not_treated_as_observed() -> None:
    snapshot = generate_history("mixed", 42)
    assert snapshot["provenance"]["evidenceClass"] == "unknown"
    artifact = calibrate(snapshot, request_for_fixture("cg3-mixed-origin", snapshot, approve=True))
    arrival = next(item for item in artifact.parameter_estimates if item.parameter_id == "arrival.mean_interarrival_time")  # noqa: E501
    assert arrival.evidence_class == "unknown"


def test_statistical_interval_is_not_an_assumption_range() -> None:
    snapshot = generate_history("golden", 43)
    artifact = calibrate(snapshot, request_for_fixture("cg3-golden-analytical", snapshot, approve=True))  # noqa: E501
    arrival = next(item for item in artifact.parameter_estimates if item.parameter_id == "arrival.mean_interarrival_time")  # noqa: E501
    assert arrival.uncertainty is not None
    assert arrival.uncertainty.kind == "poisson_rate_normal"
    capacity = next(item for item in artifact.parameter_estimates if item.parameter_id == "resource.triage-team.capacity")  # noqa: E501
    if capacity.uncertainty:
        assert capacity.uncertainty.kind == "assumption_range"


def test_malformed_snapshot_rejected() -> None:
    snapshot = generate_history("golden", 44)
    del snapshot["cases"]
    request = CalibrationRequest.model_validate(
        {
            "snapshotReference": "x",
            "snapshotFingerprint": "b" * 64,
            "operationalMapping": {"reviewed": True, "statuses": []},
        }
    )
    artifact = calibrate(snapshot, request)
    assert artifact.failure_class == "invalid_evidence"


def test_empty_history_is_insufficient() -> None:
    snapshot = generate_history("golden", 45)
    snapshot["cases"] = []
    snapshot["events"] = []
    snapshot["intervals"] = []
    from app.calibration.snapshot import content_fingerprint

    snapshot["contentFingerprint"] = content_fingerprint(snapshot)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.failure_class in {"insufficient_evidence", "invalid_evidence", "missing_assumptions"}  # noqa: E501
    assert artifact.constructed_model is None
