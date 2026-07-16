from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.domain.models import (
    ContractModel,
    ObservationConfig,
    OperationalModel,
    SimulationResult,
)

ConfidenceLevel = float
FailureCategory = Literal[
    "domain_validation",
    "integrity_failure",
    "execution_failure",
    "serialization_failure",
]


class RiskThresholds(ContractModel):
    minimum_sla_attainment: float | None = Field(default=None, ge=0, le=1)
    maximum_average_cycle_time: float | None = Field(default=None, ge=0)
    maximum_p95_cycle_time: float | None = Field(default=None, ge=0)
    maximum_time_weighted_queue_length: float | None = Field(default=None, ge=0)
    maximum_terminal_failure_rate: float | None = Field(default=None, ge=0)


class RepresentativeRunConfig(ContractModel):
    detail_mode: Literal["summary", "sampled", "full"] = "sampled"
    sampled_item_limit: int | None = Field(default=25, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_sample_limit(self) -> RepresentativeRunConfig:
        if self.detail_mode == "sampled" and self.sampled_item_limit is None:
            raise ValueError("sampled detail requires sampledItemLimit")
        if self.detail_mode != "sampled" and self.sampled_item_limit is not None:
            raise ValueError("sampledItemLimit is only valid for sampled detail")
        return self


class RepeatedSimulationRequest(ContractModel):
    schema_version: Literal["0.4.0"] = "0.4.0"
    model: OperationalModel
    base_seed: int = Field(ge=0, le=2**63 - 1)
    run_count: int = Field(default=100, ge=2, le=500)
    confidence_level: ConfidenceLevel = 0.95
    minimum_successful_run_ratio: float = Field(default=1.0, ge=0.5, le=1.0)
    observation: ObservationConfig = Field(default_factory=ObservationConfig)
    thresholds: RiskThresholds = Field(default_factory=RiskThresholds)
    representative_run: RepresentativeRunConfig = Field(
        default_factory=RepresentativeRunConfig
    )

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence_level(cls, value: float) -> float:
        if value not in (0.90, 0.95, 0.99):
            raise ValueError("confidenceLevel must be 0.90, 0.95, or 0.99")
        return value


class RunSeed(ContractModel):
    run_index: int = Field(ge=0)
    seed: int = Field(ge=0, le=2**64 - 1)


class ConfidenceInterval(ContractModel):
    level: ConfidenceLevel
    lower: float
    upper: float
    method: Literal["normal_approximation"] = "normal_approximation"
    successful_run_count: int = Field(ge=1)
    reliable_sample_size: bool


class AggregateMetric(ContractModel):
    count: int = Field(ge=1)
    mean: float
    sample_variance: float = Field(ge=0)
    standard_deviation: float = Field(ge=0)
    minimum: float
    maximum: float
    p10: float
    p50: float
    p90: float
    confidence_interval: ConfidenceInterval


class StageMetricAggregates(ContractModel):
    stage_id: str
    metrics: dict[str, AggregateMetric]


class ResourceMetricAggregates(ContractModel):
    resource_pool_id: str
    metrics: dict[str, AggregateMetric]


class RiskResult(ContractModel):
    metric: str
    operator: Literal["below", "above"]
    threshold: float
    violating_runs: int = Field(ge=0)
    valid_runs: int = Field(ge=1)
    probability: float = Field(ge=0, le=1)


class FailedRunEvidence(ContractModel):
    run_index: int = Field(ge=0)
    seed: int = Field(ge=0, le=2**64 - 1)
    category: FailureCategory
    message: str = Field(min_length=1, max_length=200)


class RunningMeanPoint(ContractModel):
    mean: float
    change_from_previous: float | None = None
    relative_change: float | None = None


class ConvergenceCheckpoint(ContractModel):
    requested_run_count: int = Field(ge=1)
    successful_run_count: int = Field(ge=0)
    metrics: dict[str, RunningMeanPoint]


class RepresentativeRunResult(ContractModel):
    run_index: int = Field(ge=0)
    seed: int = Field(ge=0, le=2**64 - 1)
    selection_method: Literal["normalized_median_vector"] = "normalized_median_vector"
    distance: float = Field(ge=0)
    median_vector: dict[str, float]
    metric_vector: dict[str, float]
    rerun_snapshot_matches: bool
    detail_mode: Literal["summary", "sampled", "full"]
    included_event_count: int = Field(ge=0)
    result: SimulationResult


class RepeatedExecutionMetadata(ContractModel):
    ordinary_run_count: int = Field(ge=0)
    ordinary_run_included_event_count: int = Field(ge=0)
    ordinary_run_retained_event_count: int = Field(ge=0)
    representative_rerun_count: int = Field(ge=0, le=1)
    maximum_simultaneously_retained_single_run_results: int = Field(ge=0, le=1)
    total_generated_event_count: int = Field(ge=0)
    returned_event_count: int = Field(ge=0)


class RepeatedIntegrityStatus(ContractModel):
    status: Literal["passed"] = "passed"
    checks_run: int = Field(ge=0)


class RepeatedSimulationResult(ContractModel):
    schema_version: Literal["0.4.0"] = "0.4.0"
    model_name: str
    requested_run_count: int = Field(ge=2, le=500)
    successful_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    successful_run_ratio: float = Field(ge=0, le=1)
    base_seed: int = Field(ge=0, le=2**63 - 1)
    seed_schedule_algorithm: Literal["sha256_first_64_bits"]
    run_seeds: list[RunSeed]
    observation: ObservationConfig
    confidence_level: ConfidenceLevel
    system_metrics: dict[str, AggregateMetric]
    stage_metrics: list[StageMetricAggregates]
    resource_pool_metrics: list[ResourceMetricAggregates]
    risks: list[RiskResult]
    convergence_method: Literal["observed_running_mean_stability"]
    convergence: list[ConvergenceCheckpoint]
    failed_runs: list[FailedRunEvidence]
    representative_run: RepresentativeRunResult
    execution: RepeatedExecutionMetadata
    integrity: RepeatedIntegrityStatus
