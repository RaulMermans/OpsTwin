from typing import Any

import pytest

from app.domain.models import EventType, OperationalModel, SimulationResult
from app.engine.simulator import run_simulation


@pytest.fixture
def baseline_result(deterministic_model_data: dict[str, Any]) -> SimulationResult:
    return run_simulation(OperationalModel.model_validate(deterministic_model_data))


def test_version_020_preserves_sprint_00_item_timings(baseline_result: SimulationResult) -> None:
    assert baseline_result.system_metrics.created_items == 5
    assert baseline_result.system_metrics.completed_items == 5
    assert baseline_result.system_metrics.terminally_failed_items == 0
    assert [item.processing_time for item in baseline_result.items] == [8, 8, 8, 8, 8]
    assert [item.waiting_time for item in baseline_result.items] == [0, 3, 6, 9, 12]
    assert [item.cycle_time for item in baseline_result.items] == [8, 11, 14, 17, 20]


def test_version_020_preserves_sprint_00_metrics(baseline_result: SimulationResult) -> None:
    metrics = baseline_result.system_metrics
    pool = baseline_result.resource_pool_metrics[0]

    assert metrics.throughput == pytest.approx(0.125, abs=1e-9)
    assert metrics.average_waiting_time == 6
    assert metrics.average_processing_time == 8
    assert metrics.average_cycle_time == 14
    assert metrics.p95_cycle_time == 20
    assert metrics.maximum_queue_length == 2
    assert metrics.sla_attainment == 1
    assert metrics.total_rework_count == 0
    assert metrics.event_count == 40
    assert pool.busy_time == 40
    assert pool.utilization == pytest.approx(1.0, abs=1e-9)
    assert pool.maximum_concurrent_usage == 1
    assert pool.total_requests == 5


def test_original_lifecycle_events_keep_exact_times(baseline_result: SimulationResult) -> None:
    lifecycle_types = {
        EventType.ITEM_CREATED,
        EventType.QUEUE_ENTERED,
        EventType.PROCESS_STARTED,
        EventType.PROCESS_COMPLETED,
        EventType.ITEM_COMPLETED,
    }
    observed = [
        (event.simulation_time, event.event_type.value, event.item_id)
        for event in baseline_result.events
        if event.event_type in lifecycle_types
    ]

    expected: list[tuple[float, str, str]] = []
    for item_number, (arrival, start, completion) in enumerate(
        zip([0, 5, 10, 15, 20], [0, 8, 16, 24, 32], [8, 16, 24, 32, 40], strict=False),
        start=1,
    ):
        item_id = f"tickets-item-{item_number}"
        expected.extend(
            [
                (arrival, "ITEM_CREATED", item_id),
                (arrival, "QUEUE_ENTERED", item_id),
                (start, "PROCESS_STARTED", item_id),
                (completion, "PROCESS_COMPLETED", item_id),
                (completion, "ITEM_COMPLETED", item_id),
            ]
        )
    assert (
        sorted(observed, key=lambda row: (int(row[2].rsplit("-", 1)[1]), lifecycle_order(row[1])))
        == expected
    )


def lifecycle_order(event_type: str) -> int:
    return [
        "ITEM_CREATED",
        "QUEUE_ENTERED",
        "PROCESS_STARTED",
        "PROCESS_COMPLETED",
        "ITEM_COMPLETED",
    ].index(event_type)


def test_repeated_fixed_runs_are_identical(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    first = run_simulation(model).model_dump(mode="json", by_alias=True)
    second = run_simulation(model).model_dump(mode="json", by_alias=True)

    assert first == second
    assert first["run"]["seed"] == 42


def test_no_queue_golden_model(deterministic_model_data: dict[str, Any]) -> None:
    deterministic_model_data["sources"][0].update(itemCount=3)
    deterministic_model_data["sources"][0]["arrival"]["interval"] = 10
    deterministic_model_data["stages"][0]["processingTime"]["value"] = 2

    result = run_simulation(OperationalModel.model_validate(deterministic_model_data))

    assert [item.waiting_time for item in result.items] == [0, 0, 0]
    assert result.system_metrics.maximum_queue_length == 0
    assert result.resource_pool_metrics[0].utilization == pytest.approx(6 / 22, abs=1e-9)


def test_equal_arrival_and_processing_ties_are_stable(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model_data["sources"][0].update(itemCount=3)
    deterministic_model_data["sources"][0]["arrival"]["interval"] = 5
    deterministic_model_data["stages"][0]["processingTime"]["value"] = 5
    model = OperationalModel.model_validate(deterministic_model_data)

    first = run_simulation(model)
    repeated = run_simulation(model)

    assert [item.waiting_time for item in first.items] == [0, 0, 0]
    assert first.system_metrics.maximum_queue_length == 1
    assert first.events == repeated.events
