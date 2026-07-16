from collections.abc import Callable
from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.models import (
    ObservationConfig,
    OperationalModel,
    ResultDetailConfig,
    SimulationRequest,
)


def test_version_020_deterministic_model_is_accepted(
    deterministic_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)

    assert model.schema_version == "0.2.0"
    assert model.sources[0].first_stage_id == "triage"
    assert model.stages[0].resource_pool_id == "agents"


def test_version_030_request_defaults_to_full_horizon_summary(
    deterministic_model_data: dict[str, Any],
) -> None:
    request = SimulationRequest.model_validate(
        {"schemaVersion": "0.3.0", "model": deterministic_model_data}
    )

    assert request.seed_override is None
    assert request.observation == ObservationConfig(warmup_duration=0)
    assert request.result_detail == ResultDetailConfig(mode="summary")


@pytest.mark.parametrize(
    "value",
    [
        {"warmupDuration": -1},
        {"measurementDuration": 0},
    ],
)
def test_invalid_observation_configuration_is_rejected(value: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ObservationConfig.model_validate(value)


@pytest.mark.parametrize(
    "value",
    [
        {"mode": "unsupported"},
        {"mode": "sampled"},
        {"mode": "sampled", "sampledItemLimit": 0},
        {"mode": "summary", "sampledItemLimit": 5},
        {"mode": "full", "sampledItemLimit": 5},
    ],
)
def test_invalid_result_detail_configuration_is_rejected(value: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ResultDetailConfig.model_validate(value)


def test_version_010_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    deterministic_model_data["schemaVersion"] = "0.1.0"

    with pytest.raises(ValidationError):
        OperationalModel.model_validate(deterministic_model_data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda model: model.update(sources=[]),
        lambda model: model.update(resourcePools=[]),
        lambda model: model.update(stages=[]),
        lambda model: model.update(routes=[]),
        lambda model: model.update(slaRules=[]),
    ],
)
def test_required_collections_cannot_be_empty(
    deterministic_model_data: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    invalid = deepcopy(deterministic_model_data)
    mutation(invalid)

    with pytest.raises(ValidationError):
        OperationalModel.model_validate(invalid)


@pytest.mark.parametrize(
    ("collection", "label"),
    [
        ("sources", "source"),
        ("resourcePools", "resource pool"),
        ("stages", "stage"),
        ("routes", "route"),
    ],
)
def test_duplicate_ids_are_rejected(
    deterministic_model_data: dict[str, Any], collection: str, label: str
) -> None:
    deterministic_model_data[collection].append(deepcopy(deterministic_model_data[collection][0]))

    with pytest.raises(ValidationError, match=f"duplicate {label} ID"):
        OperationalModel.model_validate(deterministic_model_data)


def test_invalid_resource_reference_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model_data["stages"][0]["resourcePoolId"] = "missing"

    with pytest.raises(ValidationError, match="unknown resource pool"):
        OperationalModel.model_validate(deterministic_model_data)


def test_invalid_stage_destination_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model_data["routes"][0]["options"][0] = {
        "targetType": "stage",
        "targetId": "missing",
        "probability": 1,
    }

    with pytest.raises(ValidationError, match="unknown stage target"):
        OperationalModel.model_validate(deterministic_model_data)


def test_invalid_route_probability_sum_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model_data["routes"][0]["options"] = [
        {"targetType": "completion", "probability": 0.4},
        {"targetType": "completion", "probability": 0.4},
    ]

    with pytest.raises(ValidationError, match="probabilities must sum to 1"):
        OperationalModel.model_validate(deterministic_model_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [("priority", -1), ("itemCount", 0), ("initialArrivalTime", -1)],
)
def test_invalid_source_values_are_rejected(
    deterministic_model_data: dict[str, Any], field: str, value: int
) -> None:
    deterministic_model_data["sources"][0][field] = value

    with pytest.raises(ValidationError):
        OperationalModel.model_validate(deterministic_model_data)


def test_invalid_route_origin_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    deterministic_model_data["routes"][0]["fromStageId"] = "missing"

    with pytest.raises(ValidationError, match="unknown origin stage"):
        OperationalModel.model_validate(deterministic_model_data)


def test_invalid_failure_configuration_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model_data["stages"][0]["failure"] = {
        "probability": 1.1,
        "routeId": "missing",
        "maximumReworkAttempts": -1,
    }

    with pytest.raises(ValidationError):
        OperationalModel.model_validate(deterministic_model_data)


def test_missing_failure_route_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    deterministic_model_data["stages"][0]["failure"] = {
        "probability": 0.5,
        "routeId": "missing",
        "maximumReworkAttempts": 1,
    }

    with pytest.raises(ValidationError, match="unknown failure route"):
        OperationalModel.model_validate(deterministic_model_data)
