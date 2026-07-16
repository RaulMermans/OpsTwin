from typing import Any

from app.domain.economics import EconomicSensitivityRequest
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
