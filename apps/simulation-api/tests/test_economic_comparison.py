from typing import Any

import pytest

from app.domain.economics import EconomicComparisonRequest
from app.economics.comparison import run_economic_comparison
from app.economics.tradeoffs import classify_tradeoff, incremental_cost_per_improvement


def request_data(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "0.7.0",
        "comparison": {
            "schemaVersion": "0.5.0",
            "baselineModel": model,
            "scenarios": [
                {
                    "id": "capacity",
                    "name": "Two agents",
                    "overrides": [
                        {
                            "entityType": "resourcePool",
                            "entityId": "agents",
                            "field": "capacity",
                            "value": 2,
                        }
                    ],
                }
            ],
            "execution": {"baseSeed": 42, "runCount": 2},
            "objective": {"metric": "averageCycleTime", "direction": "minimize"},
            "representativeEvidence": {
                "baseline": False,
                "topRankedScenario": False,
                "detailMode": "summary",
                "sampledItemLimit": None,
            },
        },
        "assumptions": {
            "schemaVersion": "0.7.0",
            "currency": "EUR",
            "modelTimeUnit": "minutes",
            "resourceProvisioning": [{"resourcePoolId": "agents", "costPerCapacityTimeUnit": 2}],
        },
        "interventions": [{"scenarioId": "capacity", "oneTimeCost": 120}],
    }


def test_economic_comparison_reuses_operational_runs_and_pairs_costs(
    deterministic_model_data: dict[str, Any],
) -> None:
    request = EconomicComparisonRequest.model_validate(request_data(deterministic_model_data))
    result = run_economic_comparison(request)

    scenario = result.scenarios[0]
    assert result.operational_comparison.execution.ordinary_simulation_executions == 4
    assert result.execution.economic_snapshot_evaluations == 4
    assert result.work_budget.estimated_work_units == 20
    assert scenario.paired_run_count == 2
    assert scenario.recurring_cost_delta.absolute_delta.mean > 0
    assert scenario.probability_higher_cost == 1
    assert scenario.intervention.one_time_cost == 120
    assert scenario.intervention.amortized_cost_per_period is None
    assert scenario.intervention.combined_per_period_cost is None
    assert result.execution.ordinary_run_retained_event_count == 0
    assert result.integrity.checks_run >= 22


def test_explicit_amortization_is_separate_and_reconciles(
    deterministic_model_data: dict[str, Any],
) -> None:
    data = request_data(deterministic_model_data)
    data["interventions"][0]["amortizationPeriods"] = 12
    scenario = run_economic_comparison(EconomicComparisonRequest.model_validate(data)).scenarios[0]

    assert scenario.intervention.amortized_cost_per_period == 10
    assert scenario.intervention.combined_per_period_cost == pytest.approx(
        scenario.scenario_cost.recurring_operating_cost.mean + 10
    )


@pytest.mark.parametrize(
    ("cost", "objective", "direction", "expected"),
    [
        (-1, -1, "lower", "lower_cost_and_improved"),
        (1, -1, "lower", "higher_cost_and_improved"),
        (-1, 1, "lower", "lower_cost_and_degraded"),
        (1, 1, "lower", "higher_cost_and_degraded"),
        (0, -1, "lower", "cost_flat_and_improved"),
        (0, 1, "lower", "cost_flat_and_degraded"),
        (-1, 0, "lower", "lower_cost_and_objective_flat"),
        (1, 0, "lower", "higher_cost_and_objective_flat"),
        (0, 0, "lower", "both_flat"),
    ],
)
def test_tradeoff_labels(cost: float, objective: float, direction: str, expected: str) -> None:
    assert classify_tradeoff(cost, objective, direction) == expected


def test_incremental_cost_uses_metric_direction_and_null_rules() -> None:
    assert incremental_cost_per_improvement(10, -2, "lower") == 5
    assert incremental_cost_per_improvement(-10, 2, "higher") == -5
    assert incremental_cost_per_improvement(10, 0, "lower") is None
    assert incremental_cost_per_improvement(10, 1, "lower") is None
