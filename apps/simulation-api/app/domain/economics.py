from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.domain.comparison import (
    ScenarioComparisonRequest,
    ScenarioComparisonResult,
    WorkBudgetResult,
)
from app.domain.models import ContractModel
from app.domain.repeated import AggregateMetric
from app.domain.sensitivity import (
    MetricResponseCurve,
    SensitivityRequest,
    SensitivityResult,
    SensitivityWorkBudget,
)

CostStatus = Literal["available", "unavailable", "not_configured"]
EconomicFailureCategory = Literal[
    "economic_assumption_validation",
    "economic_source_metric_missing",
    "economic_snapshot_failure",
    "economic_aggregation_failure",
    "economic_pairing_failure",
    "economic_guardrail_failure",
    "economic_serialization_failure",
]


class ResourceProvisioningAssumption(ContractModel):
    resource_pool_id: str = Field(min_length=1)
    cost_per_capacity_time_unit: float = Field(ge=0)


class StageVisitAssumption(ContractModel):
    stage_id: str = Field(min_length=1)
    cost_per_visit: float = Field(ge=0)


class HoldingCostAssumption(ContractModel):
    stage_id: str | None = Field(default=None, min_length=1)
    cost_per_item_time_unit: float = Field(ge=0)


class ReworkCostAssumption(ContractModel):
    stage_id: str | None = Field(default=None, min_length=1)
    cost_per_rework: float = Field(ge=0)


class EconomicAssumptions(ContractModel):
    schema_version: Literal["0.7.0"] = "0.7.0"
    currency: str
    model_time_unit: Literal["minutes"]
    resource_provisioning: list[ResourceProvisioningAssumption] = Field(default_factory=list)
    stage_visit: list[StageVisitAssumption] = Field(default_factory=list)
    queue_holding: list[HoldingCostAssumption] = Field(default_factory=list)
    wip_holding_cost_per_item_time_unit: float | None = Field(default=None, ge=0)
    cost_per_sla_violation: float | None = Field(default=None, ge=0)
    cost_per_terminal_failure: float | None = Field(default=None, ge=0)
    rework: list[ReworkCostAssumption] = Field(default_factory=list)
    cost_per_completed_item: float | None = Field(default=None, ge=0)
    fixed_cost_per_analysis_period: float | None = Field(default=None, ge=0)
    allow_partial_totals: Literal[False] = False

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if re.fullmatch(r"[A-Z]{3}", value) is None:
            raise ValueError("currency must be three uppercase letters")
        return value

    @model_validator(mode="after")
    def require_category(self) -> EconomicAssumptions:
        if not any(
            (
                self.resource_provisioning,
                self.stage_visit,
                self.queue_holding,
                self.wip_holding_cost_per_item_time_unit is not None,
                self.cost_per_sla_violation is not None,
                self.cost_per_terminal_failure is not None,
                self.rework,
                self.cost_per_completed_item is not None,
                self.fixed_cost_per_analysis_period is not None,
            )
        ):
            raise ValueError("at least one economic cost category must be configured")
        return self

    def validate_entities(self, resource_ids: set[str], stage_ids: set[str]) -> None:
        resource_scopes = [item.resource_pool_id for item in self.resource_provisioning]
        stage_visit_scopes = [item.stage_id for item in self.stage_visit]
        queue_scopes = [item.stage_id for item in self.queue_holding]
        rework_scopes = [item.stage_id for item in self.rework]
        for scopes, label in (
            (resource_scopes, "resource provisioning"),
            (stage_visit_scopes, "stage visit"),
            (queue_scopes, "queue holding"),
            (rework_scopes, "rework"),
        ):
            if len(scopes) != len(set(scopes)):
                raise ValueError(f"duplicate {label} assumption scope")
        unknown_resources = set(resource_scopes) - resource_ids
        unknown_stages = (
            set(stage_visit_scopes)
            | {item for item in queue_scopes if item is not None}
            | {item for item in rework_scopes if item is not None}
        ) - stage_ids
        if unknown_resources:
            raise ValueError("unknown resource assumption entity")
        if unknown_stages:
            raise ValueError("unknown stage assumption entity")


class CostComponent(ContractModel):
    category: str
    entity_id: str | None = None
    source_assumption: str | None = None
    source_metric: str | None = None
    source_quantity: float | None = None
    duration: float | None = None
    rate: float | None = None
    formula_label: str
    cost: float | None = None
    status: CostStatus
    reason: str | None = None


class CostSnapshotIntegrity(ContractModel):
    status: Literal["passed"] = "passed"
    checks_run: int = Field(ge=1)


class CostSnapshot(ContractModel):
    currency: str
    model_time_unit: Literal["minutes"]
    measurement_duration: float = Field(ge=0)
    components: list[CostComponent]
    status: Literal["available", "unavailable"]
    recurring_operating_cost: float | None
    completed_item_count: int = Field(ge=0)
    cost_per_completed_item: float | None
    configured_component_count: int = Field(ge=1)
    available_component_count: int = Field(ge=0)
    missing_components: list[str]
    integrity: CostSnapshotIntegrity


class ScenarioInterventionAssumption(ContractModel):
    scenario_id: str = Field(min_length=1)
    one_time_cost: float = Field(ge=0)
    amortization_periods: int | None = Field(default=None, ge=1)


class EconomicGuardrails(ContractModel):
    maximum_recurring_operating_cost: float | None = Field(default=None, ge=0)
    maximum_cost_per_completed_item: float | None = Field(default=None, ge=0)
    maximum_recurring_cost_increase: float | None = Field(default=None, ge=0)
    maximum_amortized_intervention_cost_per_period: float | None = Field(default=None, ge=0)


class EconomicComparisonRequest(ContractModel):
    schema_version: Literal["0.7.0"] = "0.7.0"
    comparison: ScenarioComparisonRequest
    assumptions: EconomicAssumptions
    interventions: list[ScenarioInterventionAssumption] = Field(default_factory=list)
    economic_guardrails: EconomicGuardrails = Field(default_factory=EconomicGuardrails)
    combine_operational_and_economic_eligibility: bool = False

    @model_validator(mode="after")
    def validate_relationships(self) -> EconomicComparisonRequest:
        if self.assumptions.model_time_unit != self.comparison.baseline_model.time_unit:
            raise ValueError("economic and operational model time units must match")
        scenario_ids = [item.id for item in self.comparison.scenarios]
        intervention_ids = [item.scenario_id for item in self.interventions]
        if len(intervention_ids) != len(set(intervention_ids)):
            raise ValueError("duplicate scenario intervention")
        if set(intervention_ids) - set(scenario_ids):
            raise ValueError("unknown scenario intervention")
        self.assumptions.validate_entities(
            {item.id for item in self.comparison.baseline_model.resource_pools},
            {item.id for item in self.comparison.baseline_model.stages},
        )
        return self


class CostAggregate(ContractModel):
    recurring_operating_cost: AggregateMetric
    cost_per_completed_item: AggregateMetric | None
    undefined_cost_per_completed_item_count: int = Field(ge=0)
    component_costs: dict[str, AggregateMetric]


class PairedCostDelta(ContractModel):
    absolute_delta: AggregateMetric
    relative_delta: AggregateMetric | None
    relative_delta_undefined_count: int = Field(ge=0)


class InterventionCostEvidence(ContractModel):
    one_time_cost: float | None = Field(default=None, ge=0)
    amortization_periods: int | None = Field(default=None, ge=1)
    amortized_cost_per_period: float | None = Field(default=None, ge=0)
    combined_per_period_cost: float | None = Field(default=None, ge=0)


class EconomicGuardrailResult(ContractModel):
    metric: str
    operator: Literal["lessThanOrEqual"] = "lessThanOrEqual"
    threshold: float = Field(ge=0)
    observed_value: float | None
    passed: bool | None


TradeoffClassification = Literal[
    "lower_cost_and_improved",
    "higher_cost_and_improved",
    "lower_cost_and_degraded",
    "higher_cost_and_degraded",
    "cost_flat_and_improved",
    "cost_flat_and_degraded",
    "lower_cost_and_objective_flat",
    "higher_cost_and_objective_flat",
    "both_flat",
    "mixed_or_insufficient_evidence",
]


class EconomicScenarioResult(ContractModel):
    scenario_id: str
    scenario_name: str
    status: Literal["valid", "economic_failed"]
    failure_category: EconomicFailureCategory | None = None
    baseline_cost: CostAggregate
    scenario_cost: CostAggregate | None
    recurring_cost_delta: PairedCostDelta | None
    component_cost_deltas: dict[str, PairedCostDelta]
    paired_run_count: int = Field(ge=0)
    paired_run_ratio: float = Field(ge=0, le=1)
    probability_lower_cost: float | None = Field(default=None, ge=0, le=1)
    probability_higher_cost: float | None = Field(default=None, ge=0, le=1)
    probability_tied_cost: float | None = Field(default=None, ge=0, le=1)
    objective_metric: str
    objective_mean_paired_delta: float | None
    probability_operationally_improved: float | None = Field(default=None, ge=0, le=1)
    tradeoff_classification: TradeoffClassification
    evidence_statement: str
    intervention: InterventionCostEvidence
    economic_guardrails: list[EconomicGuardrailResult]
    combined_eligibility: bool | None = None
    incremental_cost_per_observed_improvement: float | None = None
    incremental_cost_label: Literal[
        "Incremental recurring cost per observed unit of objective improvement"
    ] = "Incremental recurring cost per observed unit of objective improvement"


class EconomicObserverFailure(ContractModel):
    variant_id: str = Field(min_length=1)
    run_index: int = Field(ge=0)
    error_category: EconomicFailureCategory
    message: str = Field(min_length=1, max_length=200)


class EconomicExecutionMetadata(ContractModel):
    execution_order: Literal["shared_operational_comparison"] = "shared_operational_comparison"
    economic_snapshot_evaluations: int = Field(ge=0)
    economic_evaluation_seconds: float = Field(ge=0)
    ordinary_run_included_event_count: Literal[0] = 0
    ordinary_run_retained_event_count: Literal[0] = 0
    observer_failures: list[EconomicObserverFailure] = Field(default_factory=list)


class EconomicIntegrityStatus(ContractModel):
    status: Literal["passed"] = "passed"
    checks_run: int = Field(ge=22)


class EconomicComparisonResult(ContractModel):
    schema_version: Literal["0.7.0"] = "0.7.0"
    currency: str
    model_time_unit: Literal["minutes"]
    operational_comparison: ScenarioComparisonResult
    baseline_cost: CostAggregate
    scenarios: list[EconomicScenarioResult]
    work_budget: WorkBudgetResult
    execution: EconomicExecutionMetadata
    integrity: EconomicIntegrityStatus


EconomicCostMetric = Literal[
    "recurringOperatingCost",
    "costPerCompletedItem",
    "resourceProvisioningCost",
    "queueHoldingCost",
    "slaViolationCost",
    "failureCost",
    "reworkCost",
]


class EconomicSensitivityRequest(ContractModel):
    schema_version: Literal["0.7.0"] = "0.7.0"
    sensitivity: SensitivityRequest
    assumptions: EconomicAssumptions
    cost_metrics: list[EconomicCostMetric] = Field(min_length=1, max_length=7)
    cost_thresholds: dict[EconomicCostMetric, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_relationships(self) -> EconomicSensitivityRequest:
        if len(self.cost_metrics) != len(set(self.cost_metrics)):
            raise ValueError("economic sensitivity cost metrics must be unique")
        if any(value < 0 for value in self.cost_thresholds.values()):
            raise ValueError("economic sensitivity thresholds must be nonnegative")
        if self.assumptions.model_time_unit != self.sensitivity.baseline_model.time_unit:
            raise ValueError("economic and operational model time units must match")
        self.assumptions.validate_entities(
            {item.id for item in self.sensitivity.baseline_model.resource_pools},
            {item.id for item in self.sensitivity.baseline_model.stages},
        )
        return self


class EconomicSensitivityValueResult(ContractModel):
    parameter_value: float
    is_baseline_value: bool
    status: Literal["valid", "economic_failed"]
    failure_category: EconomicFailureCategory | None = None
    cost_metrics: dict[str, AggregateMetric]
    paired_cost_metrics: dict[str, PairedCostDelta]
    probability_lower_cost: dict[str, float]
    undefined_cost_per_completed_item_count: int = Field(ge=0)


class EconomicSensitivityExecutionMetadata(ContractModel):
    execution_order: Literal["shared_operational_sensitivity"] = "shared_operational_sensitivity"
    economic_snapshot_evaluations: int = Field(ge=0)
    economic_evaluation_seconds: float = Field(ge=0)
    ordinary_run_included_event_count: Literal[0] = 0
    ordinary_run_retained_event_count: Literal[0] = 0


class EconomicSensitivityResult(ContractModel):
    schema_version: Literal["0.7.0"] = "0.7.0"
    currency: str
    model_time_unit: Literal["minutes"]
    operational_sensitivity: SensitivityResult
    values: list[EconomicSensitivityValueResult]
    cost_response_curves: list[MetricResponseCurve]
    work_budget: SensitivityWorkBudget
    execution: EconomicSensitivityExecutionMetadata
    integrity: EconomicIntegrityStatus
