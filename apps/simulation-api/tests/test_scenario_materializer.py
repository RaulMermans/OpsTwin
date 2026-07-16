from copy import deepcopy
from typing import Any

import pytest

from app.domain.comparison import ScenarioDefinition
from app.domain.models import OperationalModel
from app.scenarios.materializer import (
    ScenarioMaterializationError,
    canonical_model_hash,
    materialize_scenario,
)


def scenario(*overrides: dict[str, object], scenario_id: str = "scenario-a") -> ScenarioDefinition:
    return ScenarioDefinition.model_validate(
        {
            "id": scenario_id,
            "name": scenario_id,
            "overrides": list(overrides),
        }
    )


def override(
    entity_type: str,
    entity_id: str,
    field: str,
    value: int | float,
) -> dict[str, object]:
    return {
        "entityType": entity_type,
        "entityId": entity_id,
        "field": field,
        "operation": "replace",
        "value": value,
    }


def test_gm030_applies_only_allowed_capacity_override(
    support_model_data: dict[str, Any],
) -> None:
    baseline = OperationalModel.model_validate(support_model_data)
    baseline_before = baseline.model_dump(mode="json", by_alias=True)

    result = materialize_scenario(
        baseline,
        scenario(override("resourcePool", "support", "capacity", 3)),
    )

    assert baseline.model_dump(mode="json", by_alias=True) == baseline_before
    assert next(pool for pool in result.model.resource_pools if pool.id == "support").capacity == 3
    assert result.applied_override_count == 1
    assert result.applied_overrides == [
        {
            "entityType": "resourcePool",
            "entityId": "support",
            "field": "capacity",
            "previousValue": 2,
            "value": 3,
        }
    ]
    assert result.baseline_model_hash == canonical_model_hash(baseline)
    assert result.scenario_model_hash == canonical_model_hash(result.model)


@pytest.mark.parametrize(
    "invalid_override, message",
    [
        (override("resourcePool", "missing", "capacity", 3), "unknown resourcePool"),
        (override("resourcePool", "support", "name", 3), "unsupported override field"),
        (override("resourcePool", "support", "capacity", 2.5), "integer"),
        (override("source", "tickets", "meanInterarrivalTime", 3), "Poisson"),
        (override("stage", "triage", "processing.fixed.value", 2), "distribution"),
    ],
)
def test_gm031_rejects_invalid_override(
    support_model_data: dict[str, Any],
    invalid_override: dict[str, object],
    message: str,
) -> None:
    baseline = OperationalModel.model_validate(support_model_data)

    with pytest.raises(ScenarioMaterializationError, match=message):
        materialize_scenario(baseline, scenario(invalid_override))


def test_gm031_rejects_duplicate_override_target(
    support_model_data: dict[str, Any],
) -> None:
    baseline = OperationalModel.model_validate(support_model_data)
    target = override("resourcePool", "support", "capacity", 3)

    with pytest.raises(ScenarioMaterializationError, match="duplicate override target"):
        materialize_scenario(baseline, scenario(target, target))


def test_gm032_multiple_materializations_are_isolated_and_deterministic(
    support_model_data: dict[str, Any],
) -> None:
    original_data = deepcopy(support_model_data)
    baseline = OperationalModel.model_validate(support_model_data)
    scenario_a = scenario(
        override("source", "tickets", "arrivalInterval", 1.5), scenario_id="a"
    )
    scenario_b = scenario(
        override("stage", "quality", "failure.probability", 0.1), scenario_id="b"
    )

    first_a = materialize_scenario(baseline, scenario_a)
    second_a = materialize_scenario(baseline, scenario_a)
    result_b = materialize_scenario(baseline, scenario_b)

    assert support_model_data == original_data
    assert baseline.sources[0].arrival.interval == 2  # type: ignore[union-attr]
    assert first_a.scenario_model_hash == second_a.scenario_model_hash
    assert first_a.model.sources[0].arrival.interval == 1.5  # type: ignore[union-attr]
    quality_b = next(stage for stage in result_b.model.stages if stage.id == "quality")
    assert quality_b.failure is not None and quality_b.failure.probability == 0.1
    quality_a = next(stage for stage in first_a.model.stages if stage.id == "quality")
    assert quality_a.failure is not None and quality_a.failure.probability == 0.25
