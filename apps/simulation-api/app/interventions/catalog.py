from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from app.domain.comparison import ScenarioOverride
from app.domain.models import ContractModel, ExponentialDistribution, OperationalModel, StageConfig

APPROXIMATION_EFFECTIVE_MEAN = "effective_mean_mixture"
APPROXIMATION_ROUTE_SHIFT = "success_route_probability_shift"
PLACEHOLDER_ITEM_COUNT = 1
MIN_EXPERIMENT_ITEMS = 20
MAX_EXPERIMENT_ITEMS = 80
DEFAULT_EXPERIMENT_ITEMS = 40
DEFAULT_RUN_COUNT = 5
DEFAULT_BASE_SEED = 20_261_127
COVERAGE_VALUES = (0.25, 0.5, 0.75, 1.0)
REDUCTION_VALUES = (0.2, 0.4, 0.6)
AUTO_COMPLETE_VALUES = (0.1, 0.25, 0.4)


class InterventionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ExperimentExecution(ContractModel):
    item_count: int = Field(
        default=DEFAULT_EXPERIMENT_ITEMS, ge=MIN_EXPERIMENT_ITEMS, le=MAX_EXPERIMENT_ITEMS
    )  # noqa: E501
    run_count: int = Field(default=DEFAULT_RUN_COUNT, ge=2, le=8)
    base_seed: int = Field(default=DEFAULT_BASE_SEED, ge=0, le=2**63 - 1)
    justification: str = (
        "Finite Poisson arrivals for a comparative lab run. "
        "This is not the calibrated model's placeholder itemCount and is not a historical case volume."  # noqa: E501
    )


class CapacityIntervention(ContractModel):
    kind: Literal["capacity"] = "capacity"
    extra_triage_capacity: int = Field(default=0, ge=0, le=3)
    extra_resolution_capacity: int = Field(default=1, ge=0, le=3)

    @model_validator(mode="after")
    def require_added_staff(self) -> CapacityIntervention:
        if self.extra_triage_capacity == 0 and self.extra_resolution_capacity == 0:
            raise ValueError("capacity expansion requires additional triage or resolution staff")
        return self


class AssistedIntervention(ContractModel):
    kind: Literal["ai_assisted"] = "ai_assisted"
    stage_id: Literal["triage", "resolution"] = "triage"
    coverage: float = Field(default=0.5, ge=0.25, le=1)
    processing_reduction: float = Field(default=0.4, ge=0.2, le=0.6)
    review_overhead_minutes: float = Field(default=0.25, ge=0, le=2)

    @model_validator(mode="after")
    def catalogued_assistance(self) -> AssistedIntervention:
        if self.coverage not in COVERAGE_VALUES:
            raise ValueError("coverage must be a catalog value")
        if self.processing_reduction not in REDUCTION_VALUES:
            raise ValueError("processingReduction must be a catalog value")
        return self


class HybridIntervention(ContractModel):
    kind: Literal["hybrid"] = "hybrid"
    auto_complete_fraction: float = Field(default=0.25, ge=0.1, le=0.4)
    coverage: float = Field(default=0, ge=0, le=1)
    processing_reduction: float = Field(default=0, ge=0, le=0.6)
    review_overhead_minutes: float = Field(default=0, ge=0, le=2)

    @model_validator(mode="after")
    def assisted_remainder_is_catalogued(self) -> HybridIntervention:
        if self.auto_complete_fraction not in AUTO_COMPLETE_VALUES:
            raise ValueError("autoCompleteFraction must be a catalog value")
        if self.coverage == 0:
            return self
        if self.coverage not in COVERAGE_VALUES:
            raise ValueError(
                "hybrid coverage must be a catalog value when AI-assisted remainder is used"
            )  # noqa: E501
        if self.processing_reduction not in REDUCTION_VALUES:
            raise ValueError(
                "hybrid processingReduction must be a catalog value when coverage is positive"
            )  # noqa: E501
        return self


InterventionConfig = Annotated[
    CapacityIntervention | AssistedIntervention | HybridIntervention,
    Field(discriminator="kind"),
]


class NamedAlternative(ContractModel):
    alternative_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")
    intervention: InterventionConfig


def _pool(model: OperationalModel, pool_id: str) -> int:
    match = next((pool for pool in model.resource_pools if pool.id == pool_id), None)
    if match is None:
        raise InterventionError(
            "unsupported_topology", f"Resource pool {pool_id} is not in the baseline model."
        )  # noqa: E501
    return match.capacity


def _stage(model: OperationalModel, stage_id: str) -> StageConfig:
    match = next((stage for stage in model.stages if stage.id == stage_id), None)
    if match is None:
        raise InterventionError(
            "unsupported_topology", f"Stage {stage_id} is not in the baseline model."
        )  # noqa: E501
    return match


def _exponential_mean(model: OperationalModel, stage_id: str) -> float:
    processing = _stage(model, stage_id).processing_time
    if not isinstance(processing, ExponentialDistribution):
        raise InterventionError(
            "unsupported_processing",
            "AI processing approximations require an exponential stage mean.",
        )
    return processing.mean


def effective_mean(
    human_mean: float, coverage: float, reduction: float, review_overhead: float
) -> float:  # noqa: E501
    assisted = human_mean * (1.0 - reduction)
    value = (1.0 - coverage) * human_mean + coverage * (assisted + review_overhead)
    if value <= 0:
        raise InterventionError(
            "invalid_intervention", "The effective mean must remain strictly positive."
        )  # noqa: E501
    return value


def _mean_override(stage_id: str, value: float) -> dict[str, Any]:
    return {
        "entityType": "stage",
        "entityId": stage_id,
        "field": "processing.exponential.mean",
        "operation": "replace",
        "value": value,
    }


def _capacity_override(pool_id: str, value: int) -> dict[str, Any]:
    return {
        "entityType": "resourcePool",
        "entityId": pool_id,
        "field": "capacity",
        "operation": "replace",
        "value": value,
    }


def _route_override(route_id: str, target_id: str, value: float) -> dict[str, Any]:
    return {
        "entityType": "route",
        "entityId": f"{route_id}:{target_id}",
        "field": "probability",
        "operation": "replace",
        "value": value,
    }


def triage_success_targets(model: OperationalModel) -> dict[tuple[str, str | None], float]:
    route = next((item for item in model.routes if item.id == "triage-success"), None)
    if route is None:
        return {}
    return {(option.target_type, option.target_id): option.probability for option in route.options}


def hybrid_compatible(model: OperationalModel) -> bool:
    targets = triage_success_targets(model)
    return ("stage", "resolution") in targets and ("completion", None) in targets


def baseline_inventory(model: OperationalModel) -> dict[str, Any]:
    targets = triage_success_targets(model)
    routing = targets.get(("stage", "resolution"))
    return {
        "template": "support-triage-resolution.1",
        "triageMean": _exponential_mean(model, "triage"),
        "resolutionMean": _exponential_mean(model, "resolution"),
        "triageCapacity": _pool(model, "triage-team"),
        "resolutionCapacity": _pool(model, "resolution-team"),
        "routingTriageToResolution": routing,
        "hybridCompatible": hybrid_compatible(model),
        "canonicalItemCount": model.sources[0].item_count,
        "queuePolicy": "fifo",
        "arrivalProcess": "poisson",
        "processingFamily": "exponential",
    }


def materialize_overrides(
    model: OperationalModel, intervention: InterventionConfig
) -> tuple[list[dict[str, Any]], list[str], str]:  # noqa: E501
    approximations: list[str] = []
    if isinstance(intervention, CapacityIntervention):
        overrides: list[dict[str, Any]] = []
        if intervention.extra_triage_capacity:
            overrides.append(
                _capacity_override(
                    "triage-team", _pool(model, "triage-team") + intervention.extra_triage_capacity
                )  # noqa: E501
            )
        if intervention.extra_resolution_capacity:
            overrides.append(
                _capacity_override(
                    "resolution-team",
                    _pool(model, "resolution-team") + intervention.extra_resolution_capacity,
                )
            )
        return overrides, approximations, "Increase human resource capacity"
    if isinstance(intervention, AssistedIntervention):
        human = _exponential_mean(model, intervention.stage_id)
        mean = effective_mean(
            human,
            float(intervention.coverage),
            float(intervention.processing_reduction),
            intervention.review_overhead_minutes,
        )
        approximations.append(APPROXIMATION_EFFECTIVE_MEAN)
        return (
            [_mean_override(intervention.stage_id, mean)],
            approximations,
            f"AI-assisted {intervention.stage_id} (effective-mean model)",
        )
    if not hybrid_compatible(model):
        raise InterventionError(
            "hybrid_route_unsupported",
            "This baseline does not support automated resolution. Select a compatible transformation baseline.",  # noqa: E501
        )
    targets = triage_success_targets(model)
    old_resolution = targets[("stage", "resolution")]
    new_resolution = old_resolution * (1.0 - float(intervention.auto_complete_fraction))
    overrides = [
        _route_override("triage-success", "resolution", new_resolution),
        _route_override("triage-success", "completion", 1.0 - new_resolution),
    ]
    approximations.append(APPROXIMATION_ROUTE_SHIFT)
    if float(intervention.coverage) > 0:
        human = _exponential_mean(model, "resolution")
        mean = effective_mean(
            human,
            float(intervention.coverage),
            float(intervention.processing_reduction),
            intervention.review_overhead_minutes,
        )
        overrides.append(_mean_override("resolution", mean))
        approximations.append(APPROXIMATION_EFFECTIVE_MEAN)
    return overrides, approximations, "Hybrid automation (route shift, no new stages)"


def scenario_overrides(
    model: OperationalModel, intervention: InterventionConfig
) -> list[ScenarioOverride]:  # noqa: E501
    raw, _, _ = materialize_overrides(model, intervention)
    return [ScenarioOverride.model_validate(item) for item in raw]
