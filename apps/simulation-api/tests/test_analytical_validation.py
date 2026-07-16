import random
from statistics import fmean

import pytest
from analytical_helpers import mm1_theory, relative_error, single_stage_model

from app.domain.models import (
    EventType,
    ExponentialDistribution,
    ObservationConfig,
    ResultDetailConfig,
    TriangularDistribution,
    UniformDistribution,
)
from app.engine.distributions import sample_distribution
from app.engine.simulator import run_simulation


def test_gm012_mm1_converges_to_queueing_theory() -> None:
    arrival_rate = 0.5
    service_rate = 1.0
    theory = mm1_theory(arrival_rate, service_rate)
    model = single_stage_model(
        item_count=8_000,
        arrival={"type": "poisson", "meanInterarrivalTime": 1 / arrival_rate},
        processing={"type": "exponential", "mean": 1 / service_rate},
    )
    result = run_simulation(
        model,
        observation=ObservationConfig(warmup_duration=2_000, measurement_duration=10_000),
        result_detail=ResultDetailConfig(mode="summary"),
    )

    actual = {
        "rho": result.resource_pool_metrics[0].utilization,
        "W": result.system_metrics.average_cycle_time,
        "Wq": result.system_metrics.average_waiting_time,
        "L": result.system_metrics.time_weighted_wip,
        "Lq": result.system_metrics.time_weighted_queue_length,
    }
    assert {name: relative_error(actual[name], theory[name]) for name in theory} == pytest.approx(
        {name: 0 for name in theory}, abs=0.15
    )


def test_gm013_littles_law_reconciles_in_stable_window() -> None:
    model = single_stage_model(
        item_count=8_000,
        arrival={"type": "poisson", "meanInterarrivalTime": 2},
        processing={"type": "exponential", "mean": 1},
    )
    metrics = run_simulation(
        model,
        observation=ObservationConfig(warmup_duration=2_000, measurement_duration=10_000),
        result_detail=ResultDetailConfig(mode="summary"),
    ).system_metrics

    assert relative_error(
        metrics.time_weighted_wip,
        metrics.completion_rate * metrics.average_cycle_time,
    ) < 0.08
    assert relative_error(
        metrics.time_weighted_queue_length,
        metrics.completion_rate * metrics.average_waiting_time,
    ) < 0.08


@pytest.mark.parametrize(
    ("distribution", "expected_mean"),
    [
        (ExponentialDistribution(type="exponential", mean=4), 4),
        (UniformDistribution(type="uniform", minimum=2, maximum=8), 5),
        (TriangularDistribution(type="triangular", minimum=1, mode=4, maximum=10), 5),
    ],
)
def test_distribution_samples_converge_to_expected_moments(
    distribution: ExponentialDistribution | UniformDistribution | TriangularDistribution,
    expected_mean: float,
) -> None:
    generator = random.Random(8401)
    samples = [sample_distribution(distribution, generator) for _ in range(20_000)]

    assert min(samples) >= 0
    if isinstance(distribution, UniformDistribution | TriangularDistribution):
        assert min(samples) >= distribution.minimum
        assert max(samples) <= distribution.maximum
    assert fmean(samples) == pytest.approx(expected_mean, rel=0.03)


def test_poisson_interarrivals_converge_and_timestamps_increase() -> None:
    model = single_stage_model(
        item_count=5_000,
        arrival={"type": "poisson", "meanInterarrivalTime": 2},
        processing={"type": "fixed", "value": 0},
    )
    result = run_simulation(model, result_detail=ResultDetailConfig(mode="full"))
    arrivals = [
        event.simulation_time
        for event in result.events
        if event.event_type is EventType.ITEM_CREATED
    ]
    intervals = [later - earlier for earlier, later in zip(arrivals, arrivals[1:], strict=False)]

    assert min(intervals) >= 0
    assert arrivals == sorted(arrivals)
    assert fmean(intervals) == pytest.approx(2, rel=0.05)


def test_gm015_probability_routes_converge_reproducibly() -> None:
    model = single_stage_model(
        item_count=5_000,
        arrival={"type": "fixed", "interval": 0.01},
        processing={"type": "fixed", "value": 0},
    )
    data = model.model_dump(mode="json", by_alias=True)
    data["stages"].extend(
        [
            {
                "id": "a", "name": "A", "resourcePoolId": "server",
                "processingTime": {"type": "fixed", "value": 0}, "queuePolicy": "fifo"
            },
            {
                "id": "b", "name": "B", "resourcePoolId": "server",
                "processingTime": {"type": "fixed", "value": 0}, "queuePolicy": "fifo"
            },
        ]
    )
    data["routes"] = [
        {
            "id": "branch", "kind": "success", "fromStageId": "service",
            "options": [
                {"targetType": "stage", "targetId": "a", "probability": 0.3},
                {"targetType": "stage", "targetId": "b", "probability": 0.7},
            ]
        },
        {
            "id": "a-complete", "kind": "success", "fromStageId": "a",
            "options": [{"targetType": "completion", "probability": 1}]
        },
        {
            "id": "b-complete", "kind": "success", "fromStageId": "b",
            "options": [{"targetType": "completion", "probability": 1}]
        },
    ]
    branch_model = model.model_validate(data)
    first = run_simulation(branch_model, result_detail=ResultDetailConfig(mode="full"))
    repeated = run_simulation(branch_model, result_detail=ResultDetailConfig(mode="full"))
    targets = [
        event.target_id
        for event in first.events
        if event.event_type is EventType.ROUTE_SELECTED and event.route_id == "branch"
    ]

    assert targets == [
        event.target_id
        for event in repeated.events
        if event.event_type is EventType.ROUTE_SELECTED and event.route_id == "branch"
    ]
    assert len(targets) == 5_000
    assert targets.count("a") / len(targets) == pytest.approx(0.3, abs=0.03)


def test_gm016_failure_probability_converges_reproducibly() -> None:
    model = single_stage_model(
        item_count=5_000,
        arrival={"type": "fixed", "interval": 0.01},
        processing={"type": "fixed", "value": 0},
        failure={"probability": 0.25, "routeId": "rework", "maximumReworkAttempts": 0},
    )
    first = run_simulation(model, result_detail=ResultDetailConfig(mode="summary"))
    repeated = run_simulation(model, result_detail=ResultDetailConfig(mode="summary"))

    assert first == repeated
    assert first.system_metrics.terminally_failed_items / 5_000 == pytest.approx(0.25, abs=0.03)
