from typing import Any

import pytest

from app.domain.economics import (
    CostSnapshot,
    EconomicAssumptions,
    EconomicSensitivityObserverFailure,
    EconomicSensitivityRequest,
)
from app.domain.models import OperationalModel, SimulationResult
from app.economics import sensitivity as economics_sensitivity
from app.economics.sensitivity import run_economic_sensitivity


def test_economic_sensitivity_reuses_one_operational_sweep(
    deterministic_model_data: dict[str, Any],
) -> None:
    request = EconomicSensitivityRequest.model_validate(
        {
            "schemaVersion": "0.7.0",
            "sensitivity": {
                "schemaVersion": "0.6.0",
                "baselineModel": deterministic_model_data,
                "target": {"entityType": "resourcePool", "entityId": "agents", "field": "capacity"},
                "values": [1, 2],
                "execution": {"baseSeed": 42, "runCount": 2},
                "metrics": ["averageCycleTime"],
            },
            "assumptions": {
                "schemaVersion": "0.7.0",
                "currency": "EUR",
                "modelTimeUnit": "minutes",
                "resourceProvisioning": [
                    {"resourcePoolId": "agents", "costPerCapacityTimeUnit": 2}
                ],
            },
            "costMetrics": [
                "recurringOperatingCost",
                "costPerCompletedItem",
                "resourceProvisioningCost",
            ],
        }
    )

    result = run_economic_sensitivity(request)

    assert result.operational_sensitivity.execution.ordinary_simulation_executions == 4
    assert result.execution.economic_snapshot_evaluations == 4
    assert result.work_budget == result.operational_sensitivity.work_budget
    assert [item.parameter_value for item in result.values] == [1, 2]
    assert result.values[0].paired_cost_metrics["recurringOperatingCost"].absolute_delta.mean == 0
    assert result.cost_response_curves[0].metric == "recurringOperatingCost"
    assert result.cost_response_curves[0].finite_differences
    assert result.execution.ordinary_run_retained_event_count == 0
    assert result.integrity.checks_run >= 22


def test_economic_sensitivity_is_reproducible(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = {
        "schemaVersion": "0.7.0",
        "sensitivity": {
            "schemaVersion": "0.6.0",
            "baselineModel": deterministic_model_data,
            "target": {"entityType": "resourcePool", "entityId": "agents", "field": "capacity"},
            "values": [1, 2],
            "execution": {"baseSeed": 7, "runCount": 2},
            "metrics": ["averageCycleTime"],
        },
        "assumptions": {
            "schemaVersion": "0.7.0",
            "currency": "EUR",
            "modelTimeUnit": "minutes",
            "fixedCostPerAnalysisPeriod": 5,
        },
        "costMetrics": ["recurringOperatingCost"],
    }
    request = EconomicSensitivityRequest.model_validate(data)
    first = run_economic_sensitivity(request).model_dump(mode="json", by_alias=True)
    second = run_economic_sensitivity(request).model_dump(mode="json", by_alias=True)
    assert first == second


def test_sensitivity_observer_failure_is_isolated_and_recorded(
    deterministic_model_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = {
        "schemaVersion": "0.7.0",
        "sensitivity": {
            "schemaVersion": "0.6.0",
            "baselineModel": deterministic_model_data,
            "target": {"entityType": "resourcePool", "entityId": "agents", "field": "capacity"},
            "values": [1, 2],
            "execution": {"baseSeed": 42, "runCount": 2},
            "metrics": ["averageCycleTime"],
        },
        "assumptions": {
            "schemaVersion": "0.7.0",
            "currency": "EUR",
            "modelTimeUnit": "minutes",
            "resourceProvisioning": [{"resourcePoolId": "agents", "costPerCapacityTimeUnit": 2}],
        },
        "costMetrics": ["recurringOperatingCost"],
    }
    original = economics_sensitivity.evaluate_cost_snapshot
    call_count = {"n": 0}

    def flaky(
        simulation_result: SimulationResult,
        model: OperationalModel,
        assumptions: EconomicAssumptions,
    ) -> CostSnapshot:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise ValueError("synthetic economic sensitivity evaluation failure")
        return original(simulation_result, model, assumptions)

    monkeypatch.setattr(economics_sensitivity, "evaluate_cost_snapshot", flaky)

    result = run_economic_sensitivity(EconomicSensitivityRequest.model_validate(data))

    baseline = next(item for item in result.values if item.is_baseline_value)
    assert baseline.status == "valid"
    assert result.execution.observer_failures == [
        EconomicSensitivityObserverFailure(
            tested_value=2,
            run_index=0,
            error_category="economic_snapshot_failure",
            message="economic evaluation raised a validation error",
        )
    ]
    for failure in result.execution.observer_failures:
        assert "/" not in failure.message
        assert "\\" not in failure.message
        assert "Traceback" not in failure.message
        assert "synthetic" not in failure.message
    assert result.integrity.checks_run >= 22
