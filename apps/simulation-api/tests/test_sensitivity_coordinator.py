from typing import Any

import pytest

from app.domain.models import (
    ObservationConfig,
    OperationalModel,
    ResultDetailConfig,
    SimulationResult,
)
from app.domain.sensitivity import SensitivityRequest
from app.engine.simulator import run_simulation
from app.sensitivity.coordinator import (
    SensitivityWorkBudgetError,
    run_sensitivity_analysis,
)


def request_data(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "0.6.0",
        "baselineModel": model,
        "target": {"entityType": "resourcePool", "entityId": "agents", "field": "capacity"},
        "values": [1, 2],
        "execution": {"baseSeed": 42, "runCount": 2},
        "metrics": ["averageCycleTime", "slaAttainment"],
        "thresholds": {"maximumAverageCycleTime": 20},
    }


def test_sensitivity_executes_run_index_then_values_with_shared_seeds(
    deterministic_model_data: dict[str, Any],
) -> None:
    calls: list[tuple[int, int, str]] = []

    def runner(
        model: OperationalModel,
        *,
        seed_override: int,
        observation: ObservationConfig,
        result_detail: ResultDetailConfig,
    ) -> SimulationResult:
        calls.append(
            (
                model.resource_pools[0].capacity,
                seed_override,
                result_detail.mode,
            )
        )
        return run_simulation(
            model,
            seed_override=seed_override,
            observation=observation,
            result_detail=result_detail,
        )

    result = run_sensitivity_analysis(
        SensitivityRequest.model_validate(request_data(deterministic_model_data)),
        simulation_runner=runner,
    )

    assert [capacity for capacity, _, _ in calls] == [1, 2, 1, 2]
    assert calls[0][1] == calls[1][1]
    assert calls[2][1] == calls[3][1]
    assert {detail for _, _, detail in calls} == {"summary"}
    assert result.execution.ordinary_run_retained_event_count == 0
    assert result.integrity.checks_run >= 18


def test_sensitivity_is_reproducible(deterministic_model_data: dict[str, Any]) -> None:
    request = SensitivityRequest.model_validate(request_data(deterministic_model_data))

    first = run_sensitivity_analysis(request).model_dump(mode="json", by_alias=True)
    second = run_sensitivity_analysis(request).model_dump(mode="json", by_alias=True)

    assert first == second


def test_failed_value_is_isolated(deterministic_model_data: dict[str, Any]) -> None:
    failed_once = False

    def runner(
        model: OperationalModel,
        *,
        seed_override: int,
        observation: ObservationConfig,
        result_detail: ResultDetailConfig,
    ) -> SimulationResult:
        nonlocal failed_once
        if model.resource_pools[0].capacity == 2 and not failed_once:
            failed_once = True
            raise RuntimeError("controlled failure")
        return run_simulation(
            model,
            seed_override=seed_override,
            observation=observation,
            result_detail=result_detail,
        )

    result = run_sensitivity_analysis(
        SensitivityRequest.model_validate(request_data(deterministic_model_data)),
        simulation_runner=runner,
    )

    assert result.values[0].status == "valid"
    assert result.values[1].status == "failed"
    assert result.values[1].failure is not None
    assert result.values[1].failure.category == "paired_ratio_failure"
    assert result.response_curves[0].points[1].mean is None


def test_work_budget_rejects_before_execution(deterministic_model_data: dict[str, Any]) -> None:
    data = request_data(deterministic_model_data)
    data["baselineModel"]["sources"][0]["itemCount"] = 1000
    data["execution"]["runCount"] = 100
    data["values"] = list(range(1, 11))

    with pytest.raises(SensitivityWorkBudgetError):
        run_sensitivity_analysis(SensitivityRequest.model_validate(data))
