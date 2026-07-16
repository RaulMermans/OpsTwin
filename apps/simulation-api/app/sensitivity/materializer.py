from __future__ import annotations

from dataclasses import dataclass

from app.domain.comparison import ScenarioDefinition, ScenarioOverride
from app.domain.models import OperationalModel
from app.domain.sensitivity import (
    SensitivityFailureCategory,
    SensitivityRequest,
    SensitivityTargetMetadata,
)
from app.scenarios.materializer import (
    ScenarioMaterializationError,
    canonical_model_hash,
    materialize_scenario,
)
from app.scenarios.registry import OverrideValidationError
from app.sensitivity.registry import validate_target_and_values


class SensitivityPreparationError(ValueError):
    def __init__(self, category: SensitivityFailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class SensitivityVariant:
    value: float
    is_baseline: bool
    model: OperationalModel
    model_hash: str


@dataclass(frozen=True)
class PreparedSensitivity:
    target: SensitivityTargetMetadata
    variants: list[SensitivityVariant]


def _registry_category(message: str) -> SensitivityFailureCategory:
    value_markers = ("must be", "between zero and one", "at least", "greater than")
    return (
        "value_validation"
        if any(marker in message for marker in value_markers)
        else "target_validation"
    )


def prepare_sensitivity(request: SensitivityRequest) -> PreparedSensitivity:
    canonical_values = sorted(request.values)
    try:
        validated = validate_target_and_values(
            request.baseline_model, request.target, canonical_values
        )
    except OverrideValidationError as error:
        raise SensitivityPreparationError(_registry_category(str(error)), str(error)) from error
    baseline_value = validated.metadata.baseline_value
    if baseline_value not in canonical_values:
        raise SensitivityPreparationError(
            "value_validation", "tested values must explicitly include the baseline value"
        )
    baseline_hash = canonical_model_hash(request.baseline_model)
    variants: list[SensitivityVariant] = []
    for original, normalized in zip(canonical_values, validated.normalized_values, strict=False):
        if original == baseline_value:
            variants.append(
                SensitivityVariant(original, True, request.baseline_model, baseline_hash)
            )
            continue
        scenario = ScenarioDefinition(
            id=f"sensitivity-{len(variants)}",
            name=f"Sensitivity value {original:g}",
            overrides=[
                ScenarioOverride(
                    entity_type=request.target.entity_type,
                    entity_id=request.target.entity_id,
                    field=request.target.field,
                    value=normalized,
                )
            ],
        )
        try:
            materialized = materialize_scenario(request.baseline_model, scenario)
        except ScenarioMaterializationError as error:
            category: SensitivityFailureCategory = (
                "domain_validation"
                if error.category == "domain_validation"
                else "materialization_validation"
            )
            raise SensitivityPreparationError(category, str(error)) from error
        variants.append(
            SensitivityVariant(
                original,
                False,
                materialized.model,
                materialized.scenario_model_hash,
            )
        )
    return PreparedSensitivity(validated.metadata, variants)
