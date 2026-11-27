from __future__ import annotations

from datetime import UTC, datetime

from app.calibration.catalog import request_for_fixture
from app.calibration.estimate import cases_created_in, estimate_arrivals, split_windows
from app.calibration.histories import generate_history
from app.calibration.snapshot import parse_utc
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
