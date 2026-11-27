from __future__ import annotations

from datetime import timedelta

from app.calibration.catalog import request_for_fixture
from app.calibration.estimate import split_windows
from app.calibration.histories import generate_history
from app.calibration.holdout import simulated_metrics
from app.calibration.snapshot import content_fingerprint, parse_utc
from app.calibration.workflow import calibrate
from app.domain.models import ObservationMetadata, SimulationResult


def test_empty_window_population_is_unavailable_not_all_completions() -> None:
    result = SimulationResult.model_construct(
        observation=ObservationMetadata(
            measurement_start=0,
            measurement_end=10,
            simulation_end=10,
            measurement_duration=10,
            created_during_window=0,
            completed_during_window=4,
            terminally_failed_during_window=0,
            active_at_measurement_end=0,
            excluded_pre_warmup_items=0,
            incomplete_at_measurement_end=0,
        ),
        items=[],
    )
    metrics = simulated_metrics(result)
    assert metrics["cycle_time_median"] is None
    assert metrics["throughput"] is None


def test_backlog_prevents_empty_system_adequacy_claim() -> None:
    snapshot = generate_history("golden", 91)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    _train_start, train_end, hold_start, _hold_end = split_windows(snapshot, request)
    created = hold_start - timedelta(minutes=30)
    snapshot["cases"].append(
        {
            **snapshot["cases"][0],
            "caseId": "backlog-open",
            "sourceReference": "backlog-open",
            "createdAt": created.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "resolvedAt": None,
            "currentStatusReference": "s-triage",
            "observationStatus": "open",
            "lifecycleCompleteness": "incomplete",
        }
    )
    snapshot["events"].append(
        {
            **snapshot["events"][0],
            "eventId": "e-backlog-c",
            "caseId": "backlog-open",
            "eventType": "case_created",
            "occurredAt": created.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "observedAt": created.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "previousValue": None,
            "newValue": "backlog-open",
            "sourceReference": "e-backlog-c",
        }
    )
    snapshot["contentFingerprint"] = content_fingerprint(snapshot)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert parse_utc(snapshot["cases"][-1]["createdAt"]) < hold_start
    assert train_end <= hold_start
    assert artifact.constructed_model is not None
    assert artifact.diagnostics.initial_backlog_at_holdout > 0
    assert artifact.validation_report is not None
    assert artifact.validation_report.validation_class == "empty_system_arrival_only"
    assert artifact.readiness_status != "validated_for_defined_scope"
    throughput = next(item for item in artifact.validation_report.targets if item.target_id == "throughput")  # noqa: E501
    assert throughput.outcome == "incompatible_metrics"


def test_replications_are_recorded_and_distinct_from_fixture_seed() -> None:
    snapshot = generate_history("golden", 92)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.execution_metadata.replication_count == request.execution_budget.max_replications  # noqa: E501
    assert artifact.execution_metadata.fixture_seed == request.random_seed
    assert request.random_seed not in artifact.execution_metadata.simulation_seeds
    assert len(set(artifact.execution_metadata.simulation_seeds)) == artifact.execution_metadata.replication_count  # noqa: E501
