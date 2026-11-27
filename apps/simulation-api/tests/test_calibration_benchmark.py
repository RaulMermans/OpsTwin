from __future__ import annotations

from app.calibration.benchmark import evaluate_profile, naive_baseline, run_suite
from app.calibration.catalog import load_fixture, request_for_fixture
from app.calibration.histories import generate_history
from app.calibration.workflow import calibrate


def test_golden_parameter_recovery_and_noisy_refusal() -> None:
    recovered = evaluate_profile("cg3-golden-analytical", 21)
    assert recovered["arrivalEstimate"] is not None
    assert recovered["arrivalRelativeError"] is not None
    assert recovered["arrivalRelativeError"] < 0.25
    assert recovered["arrivalRecovered"] is True
    assert recovered["constructionCorrect"] is True
    assert recovered["readiness"] in {"model_constructed", "validation_failed"}
    assert recovered["naiveLabel"] == "estimated_arrivals_default_service_capacity"
    refused = evaluate_profile("cg3-noisy", 21)
    assert refused["failureClass"] == "insufficient_evidence"
    assert refused["readiness"] == "insufficient_evidence"
    assert refused["falseConfidence"] is False


def test_partial_requires_assumptions_without_approval() -> None:
    snapshot = generate_history("partial", 22)
    request = request_for_fixture("cg3-partially-observable", snapshot, approve=False)
    artifact = calibrate(snapshot, request)
    assert artifact.readiness_status == "assumptions_required"


def test_nonstationary_homogeneous_poisson_is_rejected() -> None:
    row = evaluate_profile("cg3-nonstationary", 23)
    assert row["failureClass"] == "statistical_estimation_failure"


def test_naive_baseline_does_not_use_worklogs_as_service() -> None:
    snapshot = load_fixture("cg3-fully-observable", 24)
    artifact = naive_baseline(snapshot, 24)
    triage = next(item for item in artifact.parameter_estimates if item.parameter_id == "triage.processing_time.mean")  # noqa: E501
    assert triage.evidence_class == "assumed"
    assert float(triage.value) == 30


def test_suite_covers_all_profiles() -> None:
    rows = run_suite(seeds=(21,))
    profiles = {row["profile"] for row in rows}
    assert profiles == {
        "golden",
        "observable",
        "partial",
        "noisy",
        "nonstationary",
        "misspecified",
        "mixed",
        "shift",
    }
    assert len(rows) == 8
