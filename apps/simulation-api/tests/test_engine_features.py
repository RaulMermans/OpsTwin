from copy import deepcopy
from typing import Any

import pytest

from app.domain.models import EventType, OperationalModel
from app.engine.simulator import run_simulation


def test_poisson_arrivals_use_seeded_interarrival_samples(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = deepcopy(deterministic_model_data)
    source = data["sources"][0]
    source.update(itemCount=3, initialArrivalTime=2)
    source["arrival"] = {"type": "poisson", "meanInterarrivalTime": 5}
    data["stages"][0]["processingTime"] = {"type": "fixed", "value": 0}

    result = run_simulation(OperationalModel.model_validate(data), seed_override=123)
    creation_times = [
        event.simulation_time
        for event in result.events
        if event.event_type is EventType.ITEM_CREATED
    ]

    assert creation_times == pytest.approx([2, 2.2689219669514635, 2.725041393771446], abs=1e-12)


def test_generated_seed_is_returned_and_can_reproduce_run(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = deepcopy(deterministic_model_data)
    data["runConfig"] = {}
    data["sources"][0].update(itemCount=2)
    data["sources"][0]["arrival"] = {"type": "poisson", "meanInterarrivalTime": 2}
    model = OperationalModel.model_validate(data)

    generated = run_simulation(model)
    repeated = run_simulation(model, seed_override=generated.run.seed)

    assert 0 <= generated.run.seed <= 2**63 - 1
    assert generated.model_dump(mode="json", by_alias=True) == repeated.model_dump(
        mode="json", by_alias=True
    )


def test_different_seed_changes_stochastic_output(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = deepcopy(deterministic_model_data)
    data["sources"][0]["arrival"] = {"type": "poisson", "meanInterarrivalTime": 2}
    model = OperationalModel.model_validate(data)

    first = run_simulation(model, seed_override=42)
    different = run_simulation(model, seed_override=43)

    assert [event.simulation_time for event in first.events] != [
        event.simulation_time for event in different.events
    ]


def test_two_stage_deterministic_lifecycle_and_metrics(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = one_item_model(deterministic_model_data)
    data["resourcePools"].append({"id": "specialists", "name": "Specialists", "capacity": 1})
    data["stages"] = [
        stage("triage", "agents", 2),
        stage("resolve", "specialists", 3),
    ]
    data["routes"] = [
        success_route("triage-next", "triage", "stage", "resolve"),
        success_route("resolve-complete", "resolve", "completion"),
    ]

    result = run_simulation(OperationalModel.model_validate(data))
    item = result.items[0]

    assert [
        (visit.stage_id, visit.process_started_at, visit.process_completed_at)
        for visit in item.visits
    ] == [
        ("triage", 0, 2),
        ("resolve", 2, 5),
    ]
    assert item.cycle_time == 5
    assert sum(event.event_type is EventType.ITEM_COMPLETED for event in result.events) == 1
    assert [metric.busy_time for metric in result.resource_pool_metrics] == [2, 3]
    assert [metric.utilization for metric in result.resource_pool_metrics] == pytest.approx(
        [0.4, 0.6], abs=1e-9
    )


def test_probability_route_is_exact_for_seed(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = deepcopy(deterministic_model_data)
    data["sources"][0].update(itemCount=5)
    data["sources"][0]["arrival"] = {"type": "fixed", "interval": 1}
    data["stages"] = [
        stage("triage", "agents", 0),
        stage("a", "agents", 0),
        stage("b", "agents", 0),
    ]
    data["routes"] = [
        {
            "id": "triage-branch",
            "kind": "success",
            "fromStageId": "triage",
            "options": [
                {"targetType": "stage", "targetId": "a", "probability": 0.5},
                {"targetType": "stage", "targetId": "b", "probability": 0.5},
            ],
        },
        success_route("a-complete", "a", "completion"),
        success_route("b-complete", "b", "completion"),
    ]

    result = run_simulation(OperationalModel.model_validate(data), seed_override=42)
    branch_targets = [
        event.target_id
        for event in result.events
        if event.event_type is EventType.ROUTE_SELECTED and event.route_id == "triage-branch"
    ]

    assert branch_targets == ["b", "a", "a", "a", "b"]
    assert result.run.deterministic is False


def test_shared_pool_enforces_capacity_across_stages(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = deepcopy(deterministic_model_data)
    data["sources"] = [
        source("alpha", "stage-a", 0, 0),
        source("beta", "stage-b", 0, 0),
    ]
    data["stages"] = [stage("stage-a", "agents", 4), stage("stage-b", "agents", 4)]
    data["routes"] = [
        success_route("a-complete", "stage-a", "completion"),
        success_route("b-complete", "stage-b", "completion"),
    ]

    result = run_simulation(OperationalModel.model_validate(data))
    pool = result.resource_pool_metrics[0]
    visits = {item.source_id: item.visits[0] for item in result.items}

    assert visits["alpha"].waiting_time == 0
    assert visits["beta"].waiting_time == 4
    assert pool.maximum_concurrent_usage == 1
    assert pool.total_requests == 2
    assert pool.busy_time == 8
    assert pool.utilization == 1
    assert (
        next(
            metric for metric in result.stage_metrics if metric.stage_id == "stage-b"
        ).maximum_queue_length
        == 1
    )


def test_priority_is_non_preemptive_and_stable(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = deepcopy(deterministic_model_data)
    data["sources"] = [
        source("active-low", "triage", 0, 5),
        source("queued-low", "triage", 1, 5),
        source("queued-high", "triage", 1, 0),
    ]
    data["stages"] = [stage("triage", "agents", 4, queue_policy="priority")]

    result = run_simulation(OperationalModel.model_validate(data))
    starts = [
        (event.item_id, event.simulation_time)
        for event in result.events
        if event.event_type is EventType.PROCESS_STARTED
    ]

    assert starts == [
        ("active-low-item-1", 0),
        ("queued-high-item-1", 4),
        ("queued-low-item-1", 8),
    ]


def test_equal_priority_preserves_source_request_order(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = deepcopy(deterministic_model_data)
    data["sources"] = [
        source("active", "triage", 0, 2),
        source("first-queued", "triage", 1, 2),
        source("second-queued", "triage", 1, 2),
    ]
    data["stages"] = [stage("triage", "agents", 2, queue_policy="priority")]

    result = run_simulation(OperationalModel.model_validate(data))
    starts = [
        event.item_id for event in result.events if event.event_type is EventType.PROCESS_STARTED
    ]

    assert starts == ["active-item-1", "first-queued-item-1", "second-queued-item-1"]


def test_failure_rework_limit_ends_in_terminal_failure(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = one_item_model(deterministic_model_data)
    data["stages"] = [
        {
            **stage("quality", "agents", 1),
            "failure": {
                "probability": 1,
                "routeId": "quality-rework",
                "maximumReworkAttempts": 2,
            },
        }
    ]
    data["sources"][0]["firstStageId"] = "quality"
    data["routes"] = [
        success_route("quality-complete", "quality", "completion"),
        {
            "id": "quality-rework",
            "kind": "failure",
            "fromStageId": "quality",
            "options": [{"targetType": "stage", "targetId": "quality", "probability": 1}],
        },
    ]

    result = run_simulation(OperationalModel.model_validate(data))
    item = result.items[0]

    assert len(item.visits) == 3
    assert item.rework_count == 2
    assert item.terminally_failed is True
    assert item.completed is False
    assert item.cycle_time == 3
    assert result.system_metrics.completed_items == 0
    assert result.system_metrics.terminally_failed_items == 1
    assert result.system_metrics.total_rework_count == 2
    assert result.system_metrics.sla_attainment == 0
    quality = result.stage_metrics[0]
    assert quality.failure_count == 3
    assert quality.rework_count == 2
    assert sum(event.event_type is EventType.ITEM_FAILED for event in result.events) == 3
    assert sum(event.event_type is EventType.ITEM_REWORKED for event in result.events) == 2
    assert sum(event.event_type is EventType.ITEM_COMPLETED for event in result.events) == 0


def test_zero_failure_probability_preserves_success(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = one_item_model(deterministic_model_data)
    data["stages"][0]["failure"] = {
        "probability": 0,
        "routeId": "triage-rework",
        "maximumReworkAttempts": 1,
    }
    data["routes"].append(
        {
            "id": "triage-rework",
            "kind": "failure",
            "fromStageId": "triage",
            "options": [{"targetType": "stage", "targetId": "triage", "probability": 1}],
        }
    )

    result = run_simulation(OperationalModel.model_validate(data))

    assert result.system_metrics.completed_items == 1
    assert result.system_metrics.terminally_failed_items == 0
    assert result.system_metrics.total_rework_count == 0


def one_item_model(data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(data)
    result["sources"][0].update(itemCount=1)
    return result


def stage(
    stage_id: str,
    pool_id: str,
    duration: float,
    queue_policy: str = "fifo",
) -> dict[str, Any]:
    return {
        "id": stage_id,
        "name": stage_id,
        "resourcePoolId": pool_id,
        "processingTime": {"type": "fixed", "value": duration},
        "queuePolicy": queue_policy,
    }


def success_route(
    route_id: str, origin: str, target_type: str, target_id: str | None = None
) -> dict[str, Any]:
    option: dict[str, Any] = {"targetType": target_type, "probability": 1}
    if target_id is not None:
        option["targetId"] = target_id
    return {
        "id": route_id,
        "kind": "success",
        "fromStageId": origin,
        "options": [option],
    }


def source(source_id: str, first_stage: str, arrival_time: float, priority: int) -> dict[str, Any]:
    return {
        "id": source_id,
        "name": source_id,
        "itemCount": 1,
        "initialArrivalTime": arrival_time,
        "priority": priority,
        "firstStageId": first_stage,
        "arrival": {"type": "fixed", "interval": 1},
    }
