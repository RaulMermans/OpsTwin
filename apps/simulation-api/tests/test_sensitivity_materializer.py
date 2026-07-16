from copy import deepcopy
from typing import Any

import pytest

from app.domain.sensitivity import SensitivityRequest
from app.sensitivity.materializer import SensitivityPreparationError, prepare_sensitivity


def request_data(model: dict[str, Any]) -> dict[str, Any]:
    capacity = next(pool["capacity"] for pool in model["resourcePools"] if pool["id"] == "support")
    return {
        "schemaVersion": "0.6.0",
        "baselineModel": model,
        "target": {"entityType": "resourcePool", "entityId": "support", "field": "capacity"},
        "values": sorted({1, capacity, capacity + 1}),
        "execution": {"baseSeed": 42, "runCount": 3},
        "metrics": ["averageCycleTime"],
    }


def test_preparation_canonicalizes_values_and_preserves_baseline(
    support_model_data: dict[str, Any],
) -> None:
    original = deepcopy(support_model_data)
    data = request_data(support_model_data)
    data["values"] = list(reversed(data["values"]))
    prepared = prepare_sensitivity(SensitivityRequest.model_validate(data))

    assert [variant.value for variant in prepared.variants] == sorted(data["values"])
    assert sum(variant.is_baseline for variant in prepared.variants) == 1
    assert support_model_data == original
    assert prepared.target.baseline_value in data["values"]


def test_preparation_rejects_missing_baseline_value(
    support_model_data: dict[str, Any],
) -> None:
    data = request_data(support_model_data)
    data["values"] = [10, 11]

    with pytest.raises(SensitivityPreparationError) as error:
        prepare_sensitivity(SensitivityRequest.model_validate(data))

    assert error.value.category == "value_validation"


def test_route_probability_does_not_renormalize_siblings_and_invalid_sum_fails(
    support_model_data: dict[str, Any],
) -> None:
    route = support_model_data["routes"][0]
    if len(route["options"]) == 1:
        pytest.skip("fixture does not contain a probabilistic route")
    target_id = route["options"][0].get("targetId", "completion")
    data = request_data(support_model_data)
    data["target"] = {
        "entityType": "route",
        "entityId": f"{route['id']}:{target_id}",
        "field": "probability",
    }
    baseline = route["options"][0]["probability"]
    data["values"] = [baseline, min(1.0, baseline + 0.1)]

    with pytest.raises(SensitivityPreparationError) as error:
        prepare_sensitivity(SensitivityRequest.model_validate(data))

    assert error.value.category == "domain_validation"


def test_unknown_target_fails_safely(support_model_data: dict[str, Any]) -> None:
    data = request_data(support_model_data)
    data["target"]["entityId"] = "missing"

    with pytest.raises(SensitivityPreparationError) as error:
        prepare_sensitivity(SensitivityRequest.model_validate(data))

    assert error.value.category == "target_validation"
