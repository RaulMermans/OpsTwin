from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

from app.calibration.catalog import request_for_fixture
from app.calibration.contracts import ObservationWindow
from app.calibration.estimate import cases_created_in, estimate_arrivals, split_windows
from app.calibration.histories import generate_history
from app.calibration.snapshot import content_fingerprint, parse_utc
from app.calibration.workflow import calibrate


def test_arrival_estimate_ignores_holdout_creations() -> None:
    snapshot = generate_history("golden", 31)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    train_start, train_end, hold_start, hold_end = split_windows(snapshot, request)
    training_only, _diag = estimate_arrivals(snapshot, train_start, train_end, request)
    artifact = calibrate(snapshot, request)
    fitted = next(item for item in artifact.parameter_estimates if item.parameter_id == "arrival.mean_interarrival_time")  # noqa: E501
    assert fitted.value == training_only.value
    holdout_cases = cases_created_in(snapshot, hold_start, hold_end)
    assert holdout_cases
    assert parse_utc(holdout_cases[0]["createdAt"]) >= train_end


def test_windows_are_temporal_not_shuffled() -> None:
    snapshot = generate_history("observable", 32)
    request = request_for_fixture("cg3-fully-observable", snapshot, approve=True)
    train_start, train_end, hold_start, hold_end = split_windows(snapshot, request)
    assert train_start < train_end <= hold_start < hold_end
    assert train_start.tzinfo == UTC
    created = [parse_utc(case["createdAt"]) for case in snapshot["cases"]]
    assert all(isinstance(item, datetime) for item in created if item is not None)
    span = hold_end - train_start
    expected_train = train_start + timedelta(seconds=span.total_seconds() * request.estimation_configuration.training_fraction)  # noqa: E501
    assert abs((train_end - expected_train).total_seconds()) < 1


def test_holdout_only_mutations_do_not_change_training_estimates() -> None:
    snapshot = generate_history("golden", 33)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    baseline = calibrate(snapshot, request)
    train_end = parse_utc(baseline.training_configuration["end"])
    hold_start = parse_utc(baseline.validation_configuration["start"])
    assert train_end and hold_start
    mutated = deepcopy(snapshot)
    moved = 0
    for case in mutated["cases"]:
        created = parse_utc(case["createdAt"])
        if created is not None and created >= hold_start:
            case["createdAt"] = (created + timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            moved += 1
    assert moved
    mutated["contentFingerprint"] = content_fingerprint(mutated)
    mutated_request = request_for_fixture("cg3-golden-analytical", mutated, approve=True)
    after = calibrate(mutated, mutated_request)
    before_arrival = next(item.value for item in baseline.parameter_estimates if item.parameter_id == "arrival.mean_interarrival_time")  # noqa: E501
    after_arrival = next(item.value for item in after.parameter_estimates if item.parameter_id == "arrival.mean_interarrival_time")  # noqa: E501
    assert before_arrival == after_arrival
    before_triage = next(item.value for item in baseline.parameter_estimates if item.parameter_id == "triage.processing_time.mean")  # noqa: E501
    after_triage = next(item.value for item in after.parameter_estimates if item.parameter_id == "triage.processing_time.mean")  # noqa: E501
    assert before_triage == after_triage


def test_explicit_windows_outside_observation_are_rejected() -> None:
    snapshot = generate_history("golden", 34)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    request.training_window = ObservationWindow(start="2020-01-01T00:00:00.000Z", end="2020-01-02T00:00:00.000Z")  # noqa: E501
    request.validation_window = ObservationWindow(start="2020-01-02T00:00:00.000Z", end="2020-01-03T00:00:00.000Z")  # noqa: E501
    artifact = calibrate(snapshot, request)
    assert artifact.failure_class == "insufficient_evidence"
    assert artifact.constructed_model is None
