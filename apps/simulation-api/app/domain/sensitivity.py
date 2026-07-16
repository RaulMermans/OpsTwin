from __future__ import annotations

from math import isfinite
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.domain.comparison import PairedMetricResult
from app.domain.models import ContractModel, ObservationConfig, OperationalModel
from app.domain.repeated import AggregateMetric, RiskThresholds, RunSeed

SensitivityMetric = Literal[
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


class SensitivityTarget(ContractModel):
    entity_type: Literal["resourcePool", "source", "stage", "route", "slaRule"]
    entity_id: str = Field(min_length=1)
    field: str = Field(min_length=1)


class SensitivityExecutionConfig(ContractModel):
    base_seed: int = Field(ge=0, le=2**63 - 1)
    run_count: int = Field(default=50, ge=2, le=100)
    confidence_level: float = 0.95
    minimum_successful_run_ratio: float = Field(default=1.0, ge=0.5, le=1.0)
    minimum_paired_run_ratio: float = Field(default=1.0, ge=0.5, le=1.0)
    observation: ObservationConfig = Field(default_factory=ObservationConfig)

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence_level(cls, value: float) -> float:
        if value not in (0.90, 0.95, 0.99):
            raise ValueError("confidenceLevel must be 0.90, 0.95, or 0.99")
        return value


class SensitivityRequest(ContractModel):
    schema_version: Literal["0.6.0"] = "0.6.0"
    baseline_model: OperationalModel
    target: SensitivityTarget
    values: list[float] = Field(min_length=2, max_length=10)
    execution: SensitivityExecutionConfig
    metrics: list[SensitivityMetric] = Field(min_length=1, max_length=8)
    thresholds: RiskThresholds = Field(default_factory=RiskThresholds)

    @field_validator("values")
    @classmethod
    def validate_values(cls, values: list[float]) -> list[float]:
        if any(isinstance(value, bool) or not isfinite(value) for value in values):
            raise ValueError("values must contain finite numbers")
        if len(values) != len(set(values)):
            raise ValueError("values must be unique")
        return values

    @model_validator(mode="after")
    def validate_unique_metrics(self) -> SensitivityRequest:
        if len(self.metrics) != len(set(self.metrics)):
            raise ValueError("metrics must be unique")
        return self


SensitivityFailureCategory = Literal[
    "target_validation",
    "value_validation",
    "materialization_validation",
    "domain_validation",
    "execution_failure",
    "integrity_failure",
    "paired_ratio_failure",
    "serialization_failure",
]


class SensitivityFailureEvidence(ContractModel):
    category: SensitivityFailureCategory
    message: str = Field(min_length=1, max_length=200)


class SensitivityTargetMetadata(ContractModel):
    entity_type: str
    entity_id: str
    field: str
    label: str
    unit: str
    value_type: Literal["integer", "number"]
    baseline_value: float


class SensitivityWorkBudget(ContractModel):
    baseline_item_count: int = Field(ge=1)
    run_count: int = Field(ge=2, le=100)
    tested_value_count: int = Field(ge=2, le=10)
    estimated_work_units: int = Field(ge=1)
    maximum_work_units: Literal[100000] = 100000


class SensitivityValueResult(ContractModel):
    parameter_value: float
    is_baseline_value: bool
    status: Literal["valid", "failed"]
    failure: SensitivityFailureEvidence | None = None
    model_hash: str | None = None
    successful_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    successful_run_ratio: float = Field(ge=0, le=1)
    paired_run_count: int = Field(ge=0)
    paired_run_ratio: float = Field(ge=0, le=1)
    system_metrics: dict[str, AggregateMetric]
    paired_metrics: dict[str, PairedMetricResult]


class ResponsePoint(ContractModel):
    parameter_value: float
    is_baseline_value: bool
    status: Literal["valid", "failed"]
    mean: float | None = None
    confidence_interval_lower: float | None = None
    confidence_interval_upper: float | None = None
    observed_elasticity: float | None = None


class FiniteDifference(ContractModel):
    metric: str
    unit: str
    lower_parameter_value: float
    upper_parameter_value: float
    parameter_difference: float
    metric_difference: float
    finite_difference: float


class ThresholdCrossing(ContractModel):
    metric: str
    operator: Literal["greaterThanOrEqual", "lessThanOrEqual"]
    threshold: float
    lower_parameter_value: float
    upper_parameter_value: float
    lower_observed_metric: float
    upper_observed_metric: float
    direction: Literal["entered_compliance", "left_compliance"]
    label: Literal["Observed threshold crossing interval"] = "Observed threshold crossing interval"


class MetricResponseCurve(ContractModel):
    metric: str
    unit: str
    direction: str
    points: list[ResponsePoint]
    finite_differences: list[FiniteDifference]
    monotonicity: Literal[
        "observed_increasing",
        "observed_decreasing",
        "observed_flat",
        "observed_mixed",
        "insufficient_evidence",
    ]
    threshold_crossings: list[ThresholdCrossing]


class SensitivityExecutionMetadata(ContractModel):
    execution_order: Literal["run_index_then_values"] = "run_index_then_values"
    ordinary_simulation_executions: int = Field(ge=0)
    ordinary_run_included_event_count: Literal[0] = 0
    ordinary_run_retained_event_count: Literal[0] = 0


class SensitivityIntegrityStatus(ContractModel):
    status: Literal["passed"] = "passed"
    checks_run: int = Field(ge=18)


class SensitivityResult(ContractModel):
    schema_version: Literal["0.6.0"] = "0.6.0"
    baseline_model_hash: str
    target: SensitivityTargetMetadata
    original_values: list[float]
    canonical_values: list[float]
    requested_run_count: int = Field(ge=2, le=100)
    base_seed: int = Field(ge=0, le=2**63 - 1)
    seed_schedule_algorithm: Literal["sha256_first_64_bits"]
    run_seeds: list[RunSeed]
    confidence_level: float
    work_budget: SensitivityWorkBudget
    values: list[SensitivityValueResult]
    response_curves: list[MetricResponseCurve]
    execution: SensitivityExecutionMetadata
    integrity: SensitivityIntegrityStatus
