from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.domain.comparison import ScenarioDefinition
from app.domain.models import OperationalModel
from app.scenarios.registry import OverrideValidationError, apply_registered_override


class ScenarioMaterializationError(ValueError):
    """Safe scenario materialization failure with a public category."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class MaterializedScenario:
    scenario_id: str
    model: OperationalModel
    applied_override_count: int
    applied_overrides: list[dict[str, object]]
    baseline_model_hash: str
    scenario_model_hash: str


def canonical_model_hash(model: OperationalModel) -> str:
    payload = json.dumps(
        model.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _topology(model: OperationalModel) -> dict[str, Any]:
    return {
        "sources": [
            (source.id, source.first_stage_id) for source in model.sources
        ],
        "pools": [pool.id for pool in model.resource_pools],
        "stages": [
            (stage.id, stage.resource_pool_id, stage.queue_policy)
            for stage in model.stages
        ],
        "routes": [
            (
                route.id,
                route.kind,
                route.from_stage_id,
                [
                    (option.target_type, option.target_id)
                    for option in route.options
                ],
            )
            for route in model.routes
        ],
        "slaRules": [(rule.id, rule.source_id) for rule in model.sla_rules],
    }


def materialize_scenario(
    baseline: OperationalModel, scenario: ScenarioDefinition
) -> MaterializedScenario:
    data = deepcopy(baseline.model_dump(mode="json", by_alias=True))
    targets: set[tuple[str, str, str]] = set()
    applied: list[dict[str, object]] = []
    try:
        for override in scenario.overrides:
            target = (override.entity_type, override.entity_id, override.field)
            if target in targets:
                raise OverrideValidationError("duplicate override target")
            targets.add(target)
            applied.append(apply_registered_override(data, override))
    except OverrideValidationError as error:
        raise ScenarioMaterializationError("override_validation", str(error)) from error
    try:
        model = OperationalModel.model_validate(data)
    except ValidationError as error:
        raise ScenarioMaterializationError(
            "domain_validation", "Materialized scenario model is invalid"
        ) from error
    if _topology(model) != _topology(baseline):
        raise ScenarioMaterializationError(
            "materialization_validation", "Scenario topology differs from baseline"
        )
    return MaterializedScenario(
        scenario_id=scenario.id,
        model=model,
        applied_override_count=len(applied),
        applied_overrides=applied,
        baseline_model_hash=canonical_model_hash(baseline),
        scenario_model_hash=canonical_model_hash(model),
    )
