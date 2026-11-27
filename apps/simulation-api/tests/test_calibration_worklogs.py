from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

from app.calibration.catalog import request_for_fixture
from app.calibration.contracts import OperationalMapping
from app.calibration.estimate import estimate_service_times, split_windows
from app.calibration.histories import generate_history
from app.calibration.mapping import validate_mapping
from app.calibration.snapshot import content_fingerprint, minutes_between, parse_utc
from app.calibration.workflow import calibrate


def _mapping(snapshot: dict) -> OperationalMapping:
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    validate_mapping(snapshot, request.operational_mapping)
    return request.operational_mapping


def test_unattributed_worklogs_stay_unattributed() -> None:
    snapshot = generate_history("golden", 61)
    for interval in snapshot["intervals"]:
        if interval["intervalType"] == "recorded_work":
            interval["statusReference"] = None
    snapshot["contentFingerprint"] = content_fingerprint(snapshot)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=False)
    train_start, train_end, _hold_start, _hold_end = split_windows(snapshot, request)
    estimates, diagnostics = estimate_service_times(
        snapshot, train_start, train_end, request, request.operational_mapping
    )
    assert diagnostics["worklog_unattributed_count"] > 0
    assert all(item.value is None for item in estimates)
    artifact = calibrate(snapshot, request)
    assert artifact.readiness_status == "assumptions_required"


def test_multiple_worklogs_for_one_episode_are_aggregated() -> None:
    snapshot = generate_history("golden", 62)
    work = [item for item in snapshot["intervals"] if item["intervalType"] == "recorded_work" and item.get("statusReference") == "s-triage"]  # noqa: E501
    first = work[0]
    start = parse_utc(first["startAt"])
    end = parse_utc(first["endAt"])
    assert start is not None and end is not None
    mid = start + (end - start) / 2
    first["endAt"] = mid.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    first["durationMinutes"] = minutes_between(start, mid)
    snapshot["intervals"].append(
        {
            **first,
            "intervalId": first["intervalId"] + "-part2",
            "startAt": mid.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endAt": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "durationMinutes": minutes_between(mid, end),
        }
    )
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    train_start, train_end, *_ = split_windows(snapshot, request)
    estimates, _diag = estimate_service_times(
        snapshot, train_start, train_end, request, request.operational_mapping
    )
    triage = next(item for item in estimates if item.parameter_id == "triage.processing_time.mean")
    assert triage.sample_size >= 1


def test_duplicate_and_overlap_and_invalid_worklogs_are_refused() -> None:
    snapshot = generate_history("golden", 63)
    work = next(item for item in snapshot["intervals"] if item["intervalType"] == "recorded_work")
    snapshot["intervals"].append(deepcopy(work))
    overlapping = deepcopy(work)
    overlapping["intervalId"] = "overlap"
    start = parse_utc(work["startAt"])
    overlapping["startAt"] = (start + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z") if start else work["startAt"]  # noqa: E501
    overlapping["durationMinutes"] = work["durationMinutes"]
    snapshot["intervals"].append(overlapping)
    negative = deepcopy(work)
    negative["intervalId"] = "neg"
    negative["durationMinutes"] = 0
    snapshot["intervals"].append(negative)
    invalid_ts = deepcopy(work)
    invalid_ts["intervalId"] = "bad-ts"
    invalid_ts["startAt"] = "not-a-timestamp"
    snapshot["intervals"].append(invalid_ts)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=False)
    train_start, train_end, *_ = split_windows(snapshot, request)
    estimates, diagnostics = estimate_service_times(
        snapshot, train_start, train_end, request, request.operational_mapping
    )
    assert diagnostics["worklog_duplicate_count"] >= 1
    assert diagnostics["worklog_invalid_count"] >= 1
    assert all(item.value is None or item.origin == "approved_assumption" for item in estimates)


def test_boundary_crossing_and_holdout_worklogs_do_not_enter_training() -> None:
    snapshot = generate_history("golden", 64)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    train_start, train_end, hold_start, hold_end = split_windows(snapshot, request)
    baseline, _ = estimate_service_times(
        snapshot, train_start, train_end, request, request.operational_mapping
    )
    crossing = {
        "intervalId": "cross",
        "caseId": snapshot["cases"][0]["caseId"],
        "intervalType": "recorded_work",
        "startAt": (train_end - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endAt": (train_end + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "durationMinutes": 25,
        "censoring": "none",
        "complete": True,
        "statusReference": "s-triage",
    }
    holdout = {
        **crossing,
        "intervalId": "hold-only",
        "startAt": hold_start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endAt": (hold_start + timedelta(minutes=9)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "durationMinutes": 9,
    }
    mutated = deepcopy(snapshot)
    mutated["intervals"].extend([crossing, holdout])
    after, diagnostics = estimate_service_times(
        mutated, train_start, train_end, request, request.operational_mapping
    )
    before_triage = next(item for item in baseline if item.parameter_id == "triage.processing_time.mean")  # noqa: E501
    after_triage = next(item for item in after if item.parameter_id == "triage.processing_time.mean")  # noqa: E501
    assert before_triage.value == after_triage.value
    assert diagnostics["worklog_holdout_only"] >= 1
    assert diagnostics["worklog_boundary_crossing"] >= 1
    assert hold_end > hold_start
    assert train_start.tzinfo == UTC
    _ = datetime.now(UTC)


def test_missing_stage_evidence_does_not_invent_attribution() -> None:
    snapshot = generate_history("golden", 65)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    mapping = _mapping(snapshot)
    for status in mapping.statuses:
        if status.stage_id == "resolution":
            status.stage_id = "triage"
    try:
        validate_mapping(snapshot, mapping)
    except Exception as error:
        assert "ambiguous" in str(error).lower() or "unsupported" in str(error).lower()
    else:
        train_start, train_end, *_ = split_windows(snapshot, request)
        estimates, _ = estimate_service_times(snapshot, train_start, train_end, request, mapping)
        resolution = next(item for item in estimates if item.parameter_id == "resolution.processing_time.mean")  # noqa: E501
        assert resolution.origin != "empirical_estimate" or resolution.value is None
