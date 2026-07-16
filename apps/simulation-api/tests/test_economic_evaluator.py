from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.economics import EconomicAssumptions
from app.domain.models import OperationalModel
from app.economics.evaluator import evaluate_cost_snapshot
from app.engine.simulator import run_simulation


def assumptions(**updates: object) -> EconomicAssumptions:
    data: dict[str, Any] = {
        "schemaVersion": "0.7.0",
        "currency": "EUR",
        "modelTimeUnit": "minutes",
        "resourceProvisioning": [{"resourcePoolId": "agents", "costPerCapacityTimeUnit": 2}],
    }
    data.update(updates)
    return EconomicAssumptions.model_validate(data)


def test_assumptions_require_currency_finite_nonnegative_and_a_category() -> None:
    for payload in (
        {
            "schemaVersion": "0.7.0",
            "currency": "eur",
            "modelTimeUnit": "minutes",
            "fixedCostPerAnalysisPeriod": 1,
        },
        {
            "schemaVersion": "0.7.0",
            "currency": "EUR",
            "modelTimeUnit": "minutes",
            "fixedCostPerAnalysisPeriod": -1,
        },
        {"schemaVersion": "0.7.0", "currency": "EUR", "modelTimeUnit": "minutes"},
    ):
        with pytest.raises(ValidationError):
            EconomicAssumptions.model_validate(payload)


def test_resource_provisioning_uses_capacity_duration_and_rate(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(deterministic_model)
    snapshot = evaluate_cost_snapshot(result, deterministic_model, assumptions())

    component = next(
        item for item in snapshot.components if item.category == "resource_provisioning"
    )
    assert component.source_quantity == deterministic_model.resource_pools[0].capacity
    assert component.duration == result.observation.measurement_duration
    assert component.cost == pytest.approx(
        deterministic_model.resource_pools[0].capacity * result.observation.measurement_duration * 2
    )


def test_all_recurring_components_reconcile_and_zero_completion_is_null(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(deterministic_model)
    configured = assumptions(
        stageVisit=[{"stageId": "triage", "costPerVisit": 3}],
        queueHolding=[{"stageId": "triage", "costPerItemTimeUnit": 4}],
        wipHoldingCostPerItemTimeUnit=5,
        costPerSlaViolation=6,
        costPerTerminalFailure=7,
        rework=[{"costPerRework": 8}],
        costPerCompletedItem=9,
        fixedCostPerAnalysisPeriod=10,
    )
    snapshot = evaluate_cost_snapshot(result, deterministic_model, configured)

    assert snapshot.status == "available"
    assert snapshot.recurring_operating_cost == pytest.approx(
        sum(component.cost or 0 for component in snapshot.components)
    )
    assert snapshot.cost_per_completed_item == pytest.approx(
        snapshot.recurring_operating_cost / snapshot.completed_item_count
    )

    empty = result.model_copy(
        update={"system_metrics": result.system_metrics.model_copy(update={"completed_items": 0})}
    )
    assert (
        evaluate_cost_snapshot(empty, deterministic_model, configured).cost_per_completed_item
        is None
    )


def test_unknown_entities_and_duplicate_scopes_are_rejected() -> None:
    configured = assumptions(
        resourceProvisioning=[
            {"resourcePoolId": "missing", "costPerCapacityTimeUnit": 1},
            {"resourcePoolId": "missing", "costPerCapacityTimeUnit": 2},
        ]
    )
    with pytest.raises(ValueError, match="duplicate"):
        configured.validate_entities({"agents"}, {"triage"})


def test_configured_missing_evidence_is_unavailable_not_zero(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(deterministic_model).model_copy(update={"stage_metrics": []})
    configured = assumptions(
        resourceProvisioning=[],
        stageVisit=[{"stageId": "triage", "costPerVisit": 1}],
    )

    snapshot = evaluate_cost_snapshot(result, deterministic_model, configured)

    stage = next(item for item in snapshot.components if item.category == "stage_visit")
    queue = next(item for item in snapshot.components if item.category == "queue_holding")
    assert stage.status == "unavailable"
    assert stage.cost is None
    assert snapshot.status == "unavailable"
    assert snapshot.recurring_operating_cost is None
    assert queue.status == "not_configured"
    assert queue.cost == 0
