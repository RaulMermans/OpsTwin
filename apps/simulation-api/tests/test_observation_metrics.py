from typing import Any

import pytest

from app.domain.models import ObservationConfig, OperationalModel, ResultDetailConfig
from app.engine.simulator import run_simulation


def test_gm010_integrates_exact_queue_and_wip_areas(
    deterministic_model_data: dict[str, Any],
) -> None:
    result = run_simulation(
        OperationalModel.model_validate(deterministic_model_data),
        observation=ObservationConfig(),
        result_detail=ResultDetailConfig(mode="full"),
    )

    assert result.observation.measurement_duration == 40
    assert result.system_metrics.time_weighted_queue_length == pytest.approx(30 / 40)
    assert result.system_metrics.time_weighted_wip == pytest.approx(70 / 40)
    assert result.stage_metrics[0].time_weighted_queue_length == pytest.approx(30 / 40)
    assert result.resource_pool_metrics[0].busy_capacity_time == 40
    assert result.resource_pool_metrics[0].utilization == 1
    assert result.resource_pool_metrics[0].available_capacity_time == 0
    assert result.resource_pool_metrics[0].idle_capacity_proportion == 0
    assert result.resource_pool_metrics[0].mean_request_wait == 6
    assert result.system_metrics.arrival_rate == pytest.approx(5 / 40)
    assert result.system_metrics.completion_rate == pytest.approx(5 / 40)
    assert result.system_metrics.failure_rate == 0
    assert result.system_metrics.flow_efficiency == pytest.approx(40 / 70)
    assert result.stage_metrics[0].waiting_time_share == 1
    assert result.stage_metrics[0].processing_time_share == 1


def test_gm011_carries_boundary_state_and_excludes_incomplete_items(
    deterministic_model_data: dict[str, Any],
) -> None:
    result = run_simulation(
        OperationalModel.model_validate(deterministic_model_data),
        observation=ObservationConfig(warmup_duration=9, measurement_duration=10),
        result_detail=ResultDetailConfig(mode="full"),
    )

    assert result.observation.measurement_start == 9
    assert result.observation.measurement_end == 19
    assert result.observation.simulation_end == 40
    assert result.observation.created_during_window == 2
    assert result.observation.completed_during_window == 1
    assert result.observation.excluded_pre_warmup_items == 2
    assert result.observation.incomplete_at_measurement_end == 2
    assert result.observation.active_at_measurement_end == 2
    assert result.system_metrics.time_weighted_wip == pytest.approx(2.0)
    assert result.system_metrics.time_weighted_queue_length == pytest.approx(1.0)
    assert result.system_metrics.average_cycle_time == 0
