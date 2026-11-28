from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.domain.models import ContractModel, OperationalModel

SCHEMA_VERSION = "cal.1.0.0"
ENGINE_VERSION = "cg3.1.cal.1"
TEMPLATE_ID = "support-triage-resolution.1"
MAPPING_VERSION = "status-role.1"

MATERIAL_PARAMETERS = frozenset(
    {
        "arrival.mean_interarrival_time",
        "triage.processing_time.mean",
        "resolution.processing_time.mean",
        "resource.triage-team.capacity",
        "resource.resolution-team.capacity",
        "routing.triage_to_resolution",
    }
)
KNOWN_ASSUMPTION_IDS = frozenset(
    {
        "arrival.mean_interarrival_time",
        "triage.processing_time.mean",
        "resolution.processing_time.mean",
        "resource.triage-team.capacity",
        "resource.resolution-team.capacity",
        "worklog.completeness",
    }
)

EvidenceClass = Literal["observed", "derived", "assumed", "synthetic", "unknown"]
IdentifiabilityStatus = Literal[
    "identifiable",
    "partially_identifiable",
    "assumption_required",
    "not_identifiable",
    "insufficient_evidence",
]
ReadinessStatus = Literal[
    "insufficient_evidence",
    "mapping_required",
    "assumptions_required",
    "model_constructed",
    "validation_pending",
    "validation_failed",
    "validated_for_defined_scope",
]
ApprovalStatus = Literal["proposed", "approved", "rejected"]
StatusRole = Literal["queue", "processing", "review", "completed", "excluded", "unknown"]
ValidationOutcome = Literal[
    "passed_for_defined_scope",
    "failed",
    "inconclusive",
    "insufficient_evidence",
    "incompatible_metrics",
]
FailureClass = Literal[
    "invalid_evidence",
    "insufficient_evidence",
    "unsupported_topology",
    "missing_assumptions",
    "statistical_estimation_failure",
    "contract_validation_failure",
    "execution_failure",
    "historical_validation_failure",
    "authorization_failure",
    "integration_failure",
    "unsupported_parameter",
]


class ObservationWindow(ContractModel):
    start: str
    end: str
    convention: Literal["closed-start-open-end-utc"] = "closed-start-open-end-utc"


class UncertaintyInterval(ContractModel):
    kind: Literal[
        "poisson_rate_normal",
        "sample_mean_t",
        "assumption_range",
        "heuristic_sensitivity_range",
    ]
    lower: float
    upper: float
    unit: str
    notes: str


class ParameterEstimate(ContractModel):
    parameter_id: str
    target_model_path: str
    parameter_type: str
    value: float | int | str | None
    unit: str
    estimation_method: str
    evidence_class: EvidenceClass
    identifiability_status: IdentifiabilityStatus
    sample_size: int = Field(ge=0)
    uncertainty: UncertaintyInterval | None = None
    source_references: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    validation_status: Literal["not_validated", "included_in_holdout", "excluded"] = "not_validated"
    consumed_by_model: bool = True
    origin: Literal["empirical_estimate", "approved_assumption", "structural_constraint", "diagnostic_only"] = (  # noqa: E501
        "empirical_estimate"
    )


class AssumptionRecord(ContractModel):
    assumption_id: str
    affected_parameter: str
    proposed_value: float | int | str
    unit: str
    rationale: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    source: str
    approval_status: ApprovalStatus
    revision: int = Field(ge=1)
    limitations: list[str] = Field(default_factory=list)
    evidence_available: str
    operational_consequence: str


class StatusMapping(ContractModel):
    status_id: str
    role: StatusRole
    stage_id: str | None = None
    reviewed: bool = False


class OperationalMapping(ContractModel):
    mapping_version: Literal["status-role.1"] = "status-role.1"
    statuses: list[StatusMapping] = Field(default_factory=list)
    request_type_classes: dict[str, str] = Field(default_factory=dict)
    reviewed: bool = False


class EstimationConfiguration(ContractModel):
    arrival_model: Literal["homogeneous_poisson"] = "homogeneous_poisson"
    treat_worklogs_as_processing: bool = False
    min_arrival_sample: int = Field(default=8, ge=1)
    min_duration_sample: int = Field(default=8, ge=1)
    min_routing_sample: int = Field(default=5, ge=1)
    allow_assumption_based_model: bool = False
    training_fraction: float = Field(default=0.7, gt=0, lt=1)


class ValidationThresholds(ContractModel):
    arrival_volume_relative: float = Field(default=0.15, gt=0)
    throughput_relative: float = Field(default=0.15, gt=0)
    cycle_time_median_relative: float = Field(default=0.20, gt=0)
    cycle_time_p90_relative: float = Field(default=0.25, gt=0)
    min_cycle_sample_median: int = Field(default=10, ge=1)
    min_cycle_sample_p90: int = Field(default=20, ge=1)


class ExecutionBudget(ContractModel):
    max_items: int = Field(default=200, ge=1, le=500)
    max_replications: int = Field(default=3, ge=1, le=8)


class CalibrationRequest(ContractModel):
    schema_version: Literal["cal.1.0.0"] = "cal.1.0.0"
    snapshot_reference: str
    snapshot_fingerprint: str
    model_template_reference: Literal["support-triage-resolution.1"] = "support-triage-resolution.1"
    operational_mapping: OperationalMapping
    assumption_set: list[AssumptionRecord] = Field(default_factory=list)
    training_window: ObservationWindow | None = None
    validation_window: ObservationWindow | None = None
    estimation_configuration: EstimationConfiguration = Field(default_factory=EstimationConfiguration)  # noqa: E501
    execution_budget: ExecutionBudget = Field(default_factory=ExecutionBudget)
    random_seed: int = Field(default=20_260_327, ge=0, le=2**63 - 1)
    validation_thresholds: ValidationThresholds = Field(default_factory=ValidationThresholds)


class ValidationTargetResult(ContractModel):
    target_id: str
    observed: float | None
    simulated: float | None
    absolute_error: float | None
    relative_error: float | None
    sample_size_observed: int
    sample_size_simulated: int
    outcome: ValidationOutcome
    notes: str


class CalibrationValidationReport(ContractModel):
    schema_version: Literal["cal.1.0.0"] = "cal.1.0.0"
    mode: Literal["generative"]
    training_window: ObservationWindow
    validation_window: ObservationWindow
    thresholds_recorded_before_evaluation: ValidationThresholds
    historical_metrics: dict[str, float | None]
    simulated_metrics: dict[str, float | None]
    targets: list[ValidationTargetResult]
    overall_outcome: ValidationOutcome
    failed_gates: list[str] = Field(default_factory=list)
    excluded_targets: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    adequacy: str
    validation_class: str = "empty_system_generative"
    replication_count: int = 1
    requested_replications: int = 1
    excluded_replications: int = 0
    simulation_seeds: list[int] = Field(default_factory=list)
    arrivals_truncated: bool = False


class CalibrationDiagnostics(ContractModel):
    arrival_dispersion: float | None = None
    weekday_concentration: float | None = None
    homogeneous_poisson_adequate: bool | None = None
    initial_backlog_at_holdout: int = 0
    unknown_backlog_at_holdout: int = 0
    worklog_overlap_count: int = 0
    worklog_unattributed_count: int = 0
    worklog_duplicate_count: int = 0
    worklog_invalid_count: int = 0
    censored_duration_excluded: int = 0
    unsupported_transitions: list[str] = Field(default_factory=list)
    unmapped_statuses: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ExecutionMetadata(ContractModel):
    snapshot_validation_ms: float = 0
    estimation_ms: float = 0
    construction_ms: float = 0
    simulation_ms: float = 0
    validation_ms: float = 0
    total_ms: float = 0
    replication_count: int = 1
    requested_replications: int = 1
    excluded_replications: int = 0
    item_count: int = 0
    fixture_seed: int = 0
    simulation_seeds: list[int] = Field(default_factory=list)
    arrivals_truncated: bool = False


class CalibrationArtifact(ContractModel):
    calibration_id: str
    schema_version: Literal["cal.1.0.0"] = "cal.1.0.0"
    engine_version: Literal["cg3.1.cal.1"] = "cg3.1.cal.1"
    source_snapshot_fingerprint: str
    model_template_version: str
    mapping_version: str
    parameter_estimates: list[ParameterEstimate]
    assumptions: list[AssumptionRecord]
    constructed_model: OperationalModel | None = None
    model_fingerprint: str | None = None
    execution_identity: str | None = None
    training_configuration: dict[str, Any]
    validation_configuration: dict[str, Any]
    diagnostics: CalibrationDiagnostics
    readiness_status: ReadinessStatus
    provenance: dict[str, Any]
    execution_metadata: ExecutionMetadata
    validation_report: CalibrationValidationReport | None = None
    content_identity: str
    failure_class: FailureClass | None = None
    blocked_reason: str | None = None
