from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.comparison import ScenarioComparisonRequest


def comparison_data(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "0.5.0",
        "baselineModel": model,
        "scenarios": [
            {
                "id": "more-support",
                "name": "More support capacity",
                "overrides": [
                    {
                        "entityType": "resourcePool",
                        "entityId": "support",
                        "field": "capacity",
                        "operation": "replace",
                        "value": 3,
                    }
                ],
            }
        ],
        "execution": {"baseSeed": 42, "runCount": 10},
        "objective": {"metric": "slaAttainment", "direction": "maximize"},
        "guardrails": [
            {
                "metric": "averageCycleTime",
                "operator": "lessThanOrEqual",
                "value": 60,
            }
        ],
    }


def test_comparison_request_accepts_bounded_typed_contract(
    support_model_data: dict[str, Any],
) -> None:
    request = ScenarioComparisonRequest.model_validate(
        comparison_data(support_model_data)
    )

    assert request.schema_version == "0.5.0"
    assert request.execution.run_count == 10
    assert request.execution.minimum_paired_run_ratio == 1.0
    assert request.representative_evidence.detail_mode == "sampled"
    assert request.representative_evidence.sampled_item_limit == 25


def test_comparison_request_rejects_duplicate_scenario_ids(
    support_model_data: dict[str, Any],
) -> None:
    data = comparison_data(support_model_data)
    data["scenarios"].append(data["scenarios"][0])

    with pytest.raises(ValidationError, match="scenario IDs"):
        ScenarioComparisonRequest.model_validate(data)


def test_comparison_request_rejects_wrong_objective_direction(
    support_model_data: dict[str, Any],
) -> None:
    data = comparison_data(support_model_data)
    data["objective"] = {
        "metric": "averageCycleTime",
        "direction": "maximize",
    }

    with pytest.raises(ValidationError, match="objective direction"):
        ScenarioComparisonRequest.model_validate(data)


@pytest.mark.parametrize("operation", ["add", "remove", "copy"])
def test_comparison_request_rejects_unsupported_override_operation(
    support_model_data: dict[str, Any], operation: str
) -> None:
    data = comparison_data(support_model_data)
    data["scenarios"][0]["overrides"][0]["operation"] = operation

    with pytest.raises(ValidationError):
        ScenarioComparisonRequest.model_validate(data)


def test_comparison_request_rejects_invalid_representative_limit(
    support_model_data: dict[str, Any],
) -> None:
    data = comparison_data(support_model_data)
    data["representativeEvidence"] = {
        "detailMode": "full",
        "sampledItemLimit": 2,
    }

    with pytest.raises(ValidationError, match="sampledItemLimit"):
        ScenarioComparisonRequest.model_validate(data)


def test_comparison_request_rejects_unknown_guardrail_resource(
    support_model_data: dict[str, Any],
) -> None:
    data = comparison_data(support_model_data)
    data["guardrails"] = [
        {
            "metric": "resourcePoolUtilization",
            "operator": "lessThanOrEqual",
            "value": 0.9,
            "resourcePoolId": "missing",
        }
    ]

    with pytest.raises(ValidationError, match="must exist"):
        ScenarioComparisonRequest.model_validate(data)
