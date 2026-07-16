from __future__ import annotations

from typing import Literal

from pydantic import Field, StrictFloat, StrictInt, field_validator, model_validator

from app.domain.models import ContractModel, ObservationConfig, OperationalModel
from app.domain.repeated import (
    AggregateMetric,
    ConvergenceCheckpoint,
    FailedRunEvidence,
    RepresentativeRunResult,
    ResourceMetricAggregates,
    RiskResult,
    RiskThresholds,
    RunSeed,
    StageMetricAggregates,
)

MetricDirection = Literal["maximize", "minimize"]
ObjectiveMetric = Literal[
    "slaAttainment",
    "completionRate",
    "flowEfficiency",
    "averageWaitingTime",
    "averageCycleTime",
    "p95CycleTime",
    "terminalFailureRate",
    "timeWeightedWip",
    "timeWeightedQueueLength",
    "totalReworkCount",
]
GuardrailMetric = Literal[
    "slaAttainment",
    "averageCycleTime",
    "p95CycleTime",
    "terminalFailureRate",
    "timeWeightedQueueLength",
    "resourcePoolUtilization",
]

OBJECTIVE_DIRECTIONS: dict[str, MetricDirection] = {
    "slaAttainment": "maximize",
    "completionRate": "maximize",
    "flowEfficiency": "maximize",
    "averageWaitingTime": "minimize",
    "averageCycleTime": "minimize",
    "p95CycleTime": "minimize",
    "terminalFailureRate": "minimize",
    "timeWeightedWip": "minimize",
    "timeWeightedQueueLength": "minimize",
    "totalReworkCount": "minimize",
}


class ScenarioOverride(ContractModel):
    entity_type: Literal["resourcePool", "source", "stage", "route", "slaRule"]
    entity_id: str = Field(min_length=1)
    field: str = Field(min_length=1)
    operation: Literal["replace"] = "replace"
    value: StrictInt | StrictFloat


class ScenarioDefinition(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=500)
    overrides: list[ScenarioOverride] = Field(min_length=1, max_length=20)


class ComparisonExecutionConfig(ContractModel):
    base_seed: int = Field(ge=0, le=2**63 - 1)
    run_count: int = Field(default=100, ge=2, le=500)
    confidence_level: float = 0.95
    minimum_successful_run_ratio: float = Field(default=1.0, ge=0.5, le=1.0)
    minimum_paired_run_ratio: float = Field(default=1.0, ge=0.5, le=1.0)
    observation: ObservationConfig = Field(default_factory=ObservationConfig)
    thresholds: RiskThresholds = Field(default_factory=RiskThresholds)

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence_level(cls, value: float) -> float:
        if value not in (0.90, 0.95, 0.99):
            raise ValueError("confidenceLevel must be 0.90, 0.95, or 0.99")
        return value


class ComparisonObjective(ContractModel):
    metric: ObjectiveMetric
    direction: MetricDirection

    @model_validator(mode="after")
    def validate_direction(self) -> ComparisonObjective:
        if self.direction != OBJECTIVE_DIRECTIONS[self.metric]:
            raise ValueError("objective direction must match metric metadata")
        return self


class ComparisonGuardrail(ContractModel):
    metric: GuardrailMetric
    operator: Literal["lessThanOrEqual", "greaterThanOrEqual"]
    value: float
    resource_pool_id: str | None = None

    @model_validator(mode="after")
    def validate_resource_guardrail(self) -> ComparisonGuardrail:
        if self.metric == "resourcePoolUtilization":
            if not self.resource_pool_id:
                raise ValueError("resourcePoolUtilization requires resourcePoolId")
            if self.operator != "lessThanOrEqual":
                raise ValueError("resourcePoolUtilization supports a maximum guardrail")
        elif self.resource_pool_id is not None:
            raise ValueError("resourcePoolId is only valid for utilization guardrails")
        return self


class RepresentativeEvidenceConfig(ContractModel):
    baseline: bool = True
    top_ranked_scenario: bool = True
    detail_mode: Literal["summary", "sampled", "full"] = "sampled"
    sampled_item_limit: int | None = Field(default=25, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_sample_limit(self) -> RepresentativeEvidenceConfig:
        if self.detail_mode == "sampled" and self.sampled_item_limit is None:
            raise ValueError("sampled detail requires sampledItemLimit")
        if self.detail_mode != "sampled" and self.sampled_item_limit is not None:
            raise ValueError("sampledItemLimit is only valid for sampled detail")
        return self


class ScenarioComparisonRequest(ContractModel):
    schema_version: Literal["0.5.0"] = "0.5.0"
    baseline_model: OperationalModel
    scenarios: list[ScenarioDefinition] = Field(min_length=1, max_length=5)
    execution: ComparisonExecutionConfig
    objective: ComparisonObjective
    guardrails: list[ComparisonGuardrail] = Field(default_factory=list, max_length=20)
    representative_evidence: RepresentativeEvidenceConfig = Field(
        default_factory=RepresentativeEvidenceConfig
    )

    @model_validator(mode="after")
    def validate_unique_scenarios(self) -> ScenarioComparisonRequest:
        identifiers = [scenario.id for scenario in self.scenarios]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("scenario IDs must be unique")
        resource_pool_ids = {pool.id for pool in self.baseline_model.resource_pools}
        for guardrail in self.guardrails:
            if (
                guardrail.resource_pool_id is not None
                and guardrail.resource_pool_id not in resource_pool_ids
            ):
                raise ValueError("guardrail resourcePoolId must exist in baselineModel")
        return self


ScenarioFailureCategory = Literal[
    "override_validation",
    "materialization_validation",
    "domain_validation",
    "paired_execution",
    "paired_ratio_failure",
    "serialization_failure",
]


class AppliedOverrideSummary(ContractModel):
    entity_type: str
    entity_id: str
    field: str
    previous_value: float
    value: float


class ScenarioFailureEvidence(ContractModel):
    category: ScenarioFailureCategory
    message: str = Field(min_length=1, max_length=200)


class WorkBudgetResult(ContractModel):
    baseline_item_count: int = Field(ge=1)
    model_variants: int = Field(ge=2, le=6)
    run_count: int = Field(ge=2, le=500)
    estimated_total_item_executions: int = Field(ge=1)
    estimated_work_units: int = Field(ge=1)
    maximum_work_units: int = Field(ge=1)


class VariantAggregateResult(ContractModel):
    variant_id: str
    model_hash: str
    successful_run_count: int = Field(ge=1)
    failed_run_count: int = Field(ge=0)
    successful_run_ratio: float = Field(ge=0, le=1)
    system_metrics: dict[str, AggregateMetric]
    stage_metrics: list[StageMetricAggregates]
    resource_pool_metrics: list[ResourceMetricAggregates]
    risks: list[RiskResult]
    convergence: list[ConvergenceCheckpoint]
    failed_runs: list[FailedRunEvidence]


class ImprovementResult(ContractModel):
    improved_count: int = Field(ge=0)
    degraded_count: int = Field(ge=0)
    tied_count: int = Field(ge=0)
    probability_of_improvement: float = Field(ge=0, le=1)
    probability_of_degradation: float = Field(ge=0, le=1)
    probability_of_tie: float = Field(ge=0, le=1)
    valid_paired_run_count: int = Field(ge=1)


class PairedMetricResult(ContractModel):
    metric: str
    absolute_delta: AggregateMetric
    relative_delta: AggregateMetric | None
    relative_delta_undefined_count: int = Field(ge=0)
    improvement: ImprovementResult


class FactualPairedMetricResult(ContractModel):
    absolute_delta: AggregateMetric
    relative_delta: AggregateMetric | None
    relative_delta_undefined_count: int = Field(ge=0)


class RiskComparisonResult(ContractModel):
    metric: str
    threshold: float
    baseline_probability: float = Field(ge=0, le=1)
    scenario_probability: float = Field(ge=0, le=1)
    probability_point_change: float
    relative_change: float | None
    baseline_only_violates: int = Field(ge=0)
    scenario_only_violates: int = Field(ge=0)
    both_violate: int = Field(ge=0)
    neither_violates: int = Field(ge=0)
    paired_run_count: int = Field(ge=1)


class GuardrailEvaluation(ContractModel):
    metric: str
    operator: str
    threshold: float
    observed_value: float
    statistic: Literal["mean"] = "mean"
    passed: bool
    resource_pool_id: str | None = None


class ScenarioComparisonEntry(ContractModel):
    scenario_id: str
    scenario_name: str
    status: Literal["valid", "failed"]
    failure: ScenarioFailureEvidence | None = None
    baseline_model_hash: str
    scenario_model_hash: str | None = None
    applied_override_count: int = Field(ge=0)
    applied_overrides: list[AppliedOverrideSummary]
    variant: VariantAggregateResult | None = None
    requested_run_count: int = Field(ge=2, le=500)
    baseline_successful_run_count: int = Field(ge=0)
    scenario_successful_run_count: int = Field(ge=0)
    paired_run_count: int = Field(ge=0)
    paired_run_ratio: float = Field(ge=0, le=1)
    paired_run_indexes: list[int]
    baseline_only_successful_indexes: list[int]
    scenario_only_successful_indexes: list[int]
    failed_indexes: list[int]
    paired_metrics: dict[str, PairedMetricResult]
    resource_utilization_deltas: dict[str, FactualPairedMetricResult]
    risk_comparisons: list[RiskComparisonResult]
    guardrails: list[GuardrailEvaluation]
    eligible: bool
    evidence_statements: list[str] = Field(max_length=5)


class ComparativeRankingEntry(ContractModel):
    rank: int = Field(ge=1)
    scenario_id: str
    eligible: Literal[True] = True
    guardrails_passed: bool
    objective_metric: str
    objective_mean_delta: float
    probability_of_improvement: float = Field(ge=0, le=1)
    confidence_interval_width: float = Field(ge=0)
    tie_break_explanation: str


class RepresentativeVariantResult(ContractModel):
    variant_id: str
    representative: RepresentativeRunResult


class ComparisonRepresentatives(ContractModel):
    baseline: RepresentativeVariantResult | None = None
    scenario: RepresentativeVariantResult | None = None


class ComparisonExecutionMetadata(ContractModel):
    execution_order: Literal["run_index_then_baseline_then_scenarios"]
    ordinary_simulation_executions: int = Field(ge=0)
    representative_reruns: int = Field(ge=0, le=2)
    ordinary_run_included_event_count: Literal[0] = 0
    ordinary_run_retained_event_count: Literal[0] = 0
    maximum_simultaneously_retained_event_rich_results: int = Field(ge=0, le=2)
    total_generated_event_count: int = Field(ge=0)
    returned_event_count: int = Field(ge=0)


class ComparisonIntegrityStatus(ContractModel):
    status: Literal["passed"] = "passed"
    checks_run: int = Field(ge=1)


class ScenarioComparisonResult(ContractModel):
    schema_version: Literal["0.5.0"] = "0.5.0"
    baseline_model_hash: str
    requested_run_count: int = Field(ge=2, le=500)
    base_seed: int = Field(ge=0, le=2**63 - 1)
    seed_schedule_algorithm: Literal["sha256_first_64_bits"]
    run_seeds: list[RunSeed]
    confidence_level: float
    work_budget: WorkBudgetResult
    baseline: VariantAggregateResult
    scenarios: list[ScenarioComparisonEntry]
    objective: ComparisonObjective
    ranking_label: Literal["comparative ranking"] = "comparative ranking"
    ranking: list[ComparativeRankingEntry]
    representatives: ComparisonRepresentatives
    execution: ComparisonExecutionMetadata
    integrity: ComparisonIntegrityStatus
