from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.models import OperationalModel, ResultDetailConfig, SimulationResult
from app.domain.repeated import RepeatedSimulationRequest
from app.engine.integrity import SimulationIntegrityError
from app.engine.repeated import (
    RepeatedSimulationError,
    SerializationFailure,
    classify_run_failure,
    run_repeated_simulation,
)
from app.engine.seed_schedule import seed_schedule
from app.engine.simulator import run_simulation
from app.engine.snapshots import extract_metric_snapshot


def repeated_request(
    support_model_data: dict[str, Any], **updates: object
) -> RepeatedSimulationRequest:
    data: dict[str, object] = {
        "model": support_model_data,
        "baseSeed": 42,
        "runCount": 3,
        "representativeRun": {
            "detailMode": "summary",
            "sampledItemLimit": None,
        },
    }
    data.update(updates)
    return RepeatedSimulationRequest.model_validate(data)


def test_metric_snapshot_contains_scalars_but_no_evidence(
    support_model_data: dict[str, Any],
) -> None:
    result = run_simulation(
        OperationalModel.model_validate(support_model_data),
        result_detail=ResultDetailConfig(mode="summary"),
    )
    snapshot = extract_metric_snapshot(0, result)

    assert snapshot.system["eventCount"] == 164
    assert set(snapshot.stages) == {"triage", "level-1", "level-2", "quality"}
    assert set(snapshot.resources) == {"intake-quality", "support"}
    assert not hasattr(snapshot, "events")
    assert not hasattr(snapshot, "items")


def test_gm019_repeated_request_is_exactly_reproducible(
    support_model_data: dict[str, Any],
) -> None:
    request = repeated_request(support_model_data)

    assert run_repeated_simulation(request) == run_repeated_simulation(request)


def test_gm027_ordinary_runs_are_summary_and_only_representative_is_rerun(
    support_model_data: dict[str, Any],
) -> None:
    modes: list[str] = []

    def recording_runner(*args: object, **kwargs: object) -> SimulationResult:
        detail = kwargs["result_detail"]
        assert isinstance(detail, ResultDetailConfig)
        modes.append(detail.mode)
        return run_simulation(*args, **kwargs)  # type: ignore[arg-type]

    request = repeated_request(
        support_model_data,
        representativeRun={"detailMode": "sampled", "sampledItemLimit": 2},
    )
    result = run_repeated_simulation(request, simulation_runner=recording_runner)

    assert modes == ["summary", "summary", "summary", "sampled"]
    assert result.execution.ordinary_run_count == 3
    assert result.execution.ordinary_run_included_event_count == 0
    assert result.execution.ordinary_run_retained_event_count == 0
    assert result.execution.representative_rerun_count == 1
    assert result.execution.maximum_simultaneously_retained_single_run_results == 1
    assert len(result.representative_run.result.result_detail.selected_item_ids) == 2
    assert result.representative_run.included_event_count == len(
        result.representative_run.result.events
    )
    assert result.representative_run.included_event_count > 0
    assert result.representative_run.rerun_snapshot_matches is True


def test_coordinator_rejects_ordinary_result_that_retains_events(
    support_model_data: dict[str, Any],
) -> None:
    calls = 0

    def event_retaining_runner(*args: object, **kwargs: object) -> SimulationResult:
        nonlocal calls
        calls += 1
        if calls <= 3:
            kwargs["result_detail"] = ResultDetailConfig(mode="full")
        return run_simulation(*args, **kwargs)  # type: ignore[arg-type]

    with pytest.raises(RepeatedSimulationError, match="retained event evidence"):
        run_repeated_simulation(
            repeated_request(support_model_data),
            simulation_runner=event_retaining_runner,
        )


def test_gm026_failed_runs_are_reported_and_excluded(
    support_model_data: dict[str, Any],
) -> None:
    failed_seed = seed_schedule(42, 3)[1]

    def one_failure(*args: object, **kwargs: object) -> SimulationResult:
        if kwargs["seed_override"] == failed_seed:
            raise RuntimeError("controlled failure")
        return run_simulation(*args, **kwargs)  # type: ignore[arg-type]

    result = run_repeated_simulation(
        repeated_request(support_model_data, minimumSuccessfulRunRatio=0.5),
        simulation_runner=one_failure,
    )

    assert result.successful_run_count == 2
    assert result.failed_run_count == 1
    assert result.successful_run_ratio == pytest.approx(2 / 3)
    assert result.failed_runs[0].seed == failed_seed
    assert result.failed_runs[0].category == "execution_failure"
    assert all(metric.count == 2 for metric in result.system_metrics.values())
    assert all(
        metric.count == 2
        for stage in result.stage_metrics
        for metric in stage.metrics.values()
    )
    assert all(
        metric.count == 2
        for resource in result.resource_pool_metrics
        for metric in resource.metrics.values()
    )


def test_gm026_minimum_success_ratio_is_enforced(
    support_model_data: dict[str, Any],
) -> None:
    failed_seeds = set(seed_schedule(42, 3)[1:])

    def two_failures(*args: object, **kwargs: object) -> SimulationResult:
        if kwargs["seed_override"] in failed_seeds:
            raise RuntimeError("controlled failure")
        return run_simulation(*args, **kwargs)  # type: ignore[arg-type]

    with pytest.raises(RepeatedSimulationError, match="successful-run ratio"):
        run_repeated_simulation(
            repeated_request(support_model_data, minimumSuccessfulRunRatio=1.0),
            simulation_runner=two_failures,
        )


def test_gm028_convergence_checkpoints_are_bounded_and_ordered(
    support_model_data: dict[str, Any],
) -> None:
    request = repeated_request(support_model_data, runCount=12)
    result = run_repeated_simulation(request)

    assert [point.requested_run_count for point in result.convergence] == [10, 12]
    assert [point.successful_run_count for point in result.convergence] == [10, 12]
    assert all(
        point.metrics["slaAttainment"].mean >= 0 for point in result.convergence
    )
    assert result.convergence_method == "observed_running_mean_stability"


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (SimulationIntegrityError("test", "private"), "integrity_failure"),
        (SerializationFailure("private"), "serialization_failure"),
        (RuntimeError("private"), "execution_failure"),
    ],
)
def test_failure_categories_are_safe(error: Exception, category: str) -> None:
    failure = classify_run_failure(1, 99, error)

    assert failure.category == category
    assert "private" not in failure.message


def test_domain_validation_failure_category_is_safe(
    support_model_data: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError) as captured:
        RepeatedSimulationRequest(
            model=support_model_data, baseSeed=42, runCount=1
        )

    failure = classify_run_failure(0, 99, captured.value)
    assert failure.category == "domain_validation"
    assert "runCount" not in failure.message


def test_representative_full_mode_retains_only_one_full_result(
    support_model_data: dict[str, Any],
) -> None:
    result = run_repeated_simulation(
        repeated_request(
            support_model_data,
            representativeRun={"detailMode": "full", "sampledItemLimit": None},
        )
    )

    representative = result.representative_run.result
    assert representative.result_detail.included_event_count == (
        representative.result_detail.total_event_count
    )
    assert result.execution.maximum_simultaneously_retained_single_run_results == 1


Runner = Callable[..., SimulationResult]
