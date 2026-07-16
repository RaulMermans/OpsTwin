from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.sensitivity import SensitivityRequest


def sensitivity_data(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "0.6.0",
        "baselineModel": model,
        "target": {
            "entityType": "resourcePool",
            "entityId": "support",
            "field": "capacity",
        },
        "values": [1, 2, 3],
        "execution": {"baseSeed": 42, "runCount": 10},
        "metrics": ["averageCycleTime", "slaAttainment"],
        "thresholds": {"minimumSlaAttainment": 0.9},
    }


def test_sensitivity_request_accepts_bounded_typed_contract(
    support_model_data: dict[str, Any],
) -> None:
    request = SensitivityRequest.model_validate(sensitivity_data(support_model_data))

    assert request.schema_version == "0.6.0"
    assert request.values == [1.0, 2.0, 3.0]
    assert request.execution.minimum_paired_run_ratio == 1.0
    assert request.metrics == ["averageCycleTime", "slaAttainment"]


@pytest.mark.parametrize("values", [[1], list(range(11)), [1, 1, 2]])
def test_sensitivity_request_rejects_invalid_value_sets(
    support_model_data: dict[str, Any], values: list[int]
) -> None:
    data = sensitivity_data(support_model_data)
    data["values"] = values

    with pytest.raises(ValidationError):
        SensitivityRequest.model_validate(data)


def test_sensitivity_request_rejects_duplicate_metrics(
    support_model_data: dict[str, Any],
) -> None:
    data = sensitivity_data(support_model_data)
    data["metrics"] = ["averageCycleTime", "averageCycleTime"]

    with pytest.raises(ValidationError, match="metrics must be unique"):
        SensitivityRequest.model_validate(data)
