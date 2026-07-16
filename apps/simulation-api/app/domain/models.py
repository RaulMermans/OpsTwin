from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from math import isclose
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(value: str) -> str:
    """Convert a snake_case Python field name to lower camel case."""
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    """Base contract with camel-case aliases and strict fields."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        allow_inf_nan=False,
    )


class FixedArrival(ContractModel):
    type: Literal["fixed"]
    interval: float = Field(gt=0)


class PoissonArrival(ContractModel):
    type: Literal["poisson"]
    mean_interarrival_time: float = Field(gt=0)


ArrivalConfig = Annotated[FixedArrival | PoissonArrival, Field(discriminator="type")]


class FixedDistribution(ContractModel):
    type: Literal["fixed"]
    value: float = Field(ge=0)


class ExponentialDistribution(ContractModel):
    type: Literal["exponential"]
    mean: float = Field(gt=0)


class UniformDistribution(ContractModel):
    type: Literal["uniform"]
    minimum: float = Field(ge=0)
    maximum: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> UniformDistribution:
        if self.minimum > self.maximum:
            raise ValueError("uniform minimum must not exceed maximum")
        return self


class TriangularDistribution(ContractModel):
    type: Literal["triangular"]
    minimum: float = Field(ge=0)
    mode: float = Field(ge=0)
    maximum: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> TriangularDistribution:
        if not self.minimum <= self.mode <= self.maximum:
            raise ValueError("triangular parameters must satisfy minimum <= mode <= maximum")
        return self


ProcessingDistribution = Annotated[
    FixedDistribution | ExponentialDistribution | UniformDistribution | TriangularDistribution,
    Field(discriminator="type"),
]


class RunConfig(ContractModel):
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)


class ObservationConfig(ContractModel):
    warmup_duration: float = Field(default=0, ge=0)
    measurement_duration: float | None = Field(default=None, gt=0)


class ResultDetailConfig(ContractModel):
    mode: Literal["summary", "sampled", "full"] = "summary"
    sampled_item_limit: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_sample_limit(self) -> ResultDetailConfig:
        if self.mode == "sampled" and self.sampled_item_limit is None:
            raise ValueError("sampled mode requires sampledItemLimit")
        if self.mode != "sampled" and self.sampled_item_limit is not None:
            raise ValueError("sampledItemLimit is only valid in sampled mode")
        return self


class SourceConfig(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    item_count: int = Field(ge=1)
    initial_arrival_time: float = Field(ge=0)
    priority: int = Field(ge=0)
    first_stage_id: str = Field(min_length=1)
    arrival: ArrivalConfig


class ResourcePoolConfig(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    capacity: int = Field(ge=1)


class FailureConfig(ContractModel):
    probability: float = Field(ge=0, le=1)
    route_id: str = Field(min_length=1)
    maximum_rework_attempts: int = Field(ge=0)


class StageConfig(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    resource_pool_id: str = Field(min_length=1)
    processing_time: ProcessingDistribution
    queue_policy: Literal["fifo", "priority"]
    failure: FailureConfig | None = None


class RouteOption(ContractModel):
    target_type: Literal["stage", "completion"]
    target_id: str | None = None
    probability: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_target(self) -> RouteOption:
        if self.target_type == "stage" and not self.target_id:
            raise ValueError("stage route option requires targetId")
        if self.target_type == "completion" and self.target_id is not None:
            raise ValueError("completion route option cannot define targetId")
        return self


class RouteConfig(ContractModel):
    id: str = Field(min_length=1)
    kind: Literal["success", "failure"]
    from_stage_id: str = Field(min_length=1)
    options: list[RouteOption] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_probabilities(self) -> RouteConfig:
        total = sum(option.probability for option in self.options)
        if not isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError("route probabilities must sum to 1")
        if self.kind == "failure":
            option = self.options[0]
            if len(self.options) != 1 or option.probability != 1 or option.target_type != "stage":
                raise ValueError("failure route must contain one deterministic stage target")
        return self


class SlaRule(ContractModel):
    id: str = Field(min_length=1)
    target_duration: float = Field(ge=0)
    source_id: str | None = None


class OperationalModel(ContractModel):
    schema_version: Literal["0.2.0"]
    name: str = Field(min_length=1)
    time_unit: Literal["minutes"]
    run_config: RunConfig
    sources: list[SourceConfig] = Field(min_length=1)
    resource_pools: list[ResourcePoolConfig] = Field(min_length=1)
    stages: list[StageConfig] = Field(min_length=1)
    routes: list[RouteConfig] = Field(min_length=1)
    sla_rules: list[SlaRule] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> OperationalModel:
        source_ids = _unique_ids("source", self.sources)
        pool_ids = _unique_ids("resource pool", self.resource_pools)
        stage_ids = _unique_ids("stage", self.stages)
        route_ids = _unique_ids("route", self.routes)
        _unique_ids("SLA rule", self.sla_rules)

        for source in self.sources:
            if source.first_stage_id not in stage_ids:
                raise ValueError(f"source {source.id} references unknown first stage")
        for stage in self.stages:
            if stage.resource_pool_id not in pool_ids:
                raise ValueError(f"stage {stage.id} references unknown resource pool")
        for route in self.routes:
            if route.from_stage_id not in stage_ids:
                raise ValueError(f"route {route.id} references unknown origin stage")
            for option in route.options:
                if option.target_type == "stage" and option.target_id not in stage_ids:
                    raise ValueError(f"route {route.id} references unknown stage target")
        for stage in self.stages:
            success_routes = [
                route
                for route in self.routes
                if route.kind == "success" and route.from_stage_id == stage.id
            ]
            if len(success_routes) != 1:
                raise ValueError(f"stage {stage.id} must have exactly one success route")
            if stage.failure is not None:
                failure_route = next(
                    (route for route in self.routes if route.id == stage.failure.route_id), None
                )
                if failure_route is None or failure_route.id not in route_ids:
                    raise ValueError(f"stage {stage.id} references unknown failure route")
                if failure_route.kind != "failure" or failure_route.from_stage_id != stage.id:
                    raise ValueError(f"stage {stage.id} failure route is not valid for that stage")
        for rule in self.sla_rules:
            if rule.source_id is not None and rule.source_id not in source_ids:
                raise ValueError(f"SLA rule {rule.id} references unknown source")
        return self


class Identified(Protocol):
    id: str


def _unique_ids(label: str, values: Sequence[Identified]) -> set[str]:
    ids: set[str] = set()
    for value in values:
        identifier = value.id
        if identifier in ids:
            raise ValueError(f"duplicate {label} ID: {identifier}")
        ids.add(identifier)
    return ids


class EventType(StrEnum):
    ITEM_CREATED = "ITEM_CREATED"
    QUEUE_ENTERED = "QUEUE_ENTERED"
    RESOURCE_REQUESTED = "RESOURCE_REQUESTED"
    PROCESS_STARTED = "PROCESS_STARTED"
    PROCESS_COMPLETED = "PROCESS_COMPLETED"
    RESOURCE_RELEASED = "RESOURCE_RELEASED"
    ROUTE_SELECTED = "ROUTE_SELECTED"
    ITEM_FAILED = "ITEM_FAILED"
    ITEM_REWORKED = "ITEM_REWORKED"
    ITEM_COMPLETED = "ITEM_COMPLETED"


class SimulationEvent(ContractModel):
    simulation_time: float = Field(ge=0)
    sequence: int = Field(ge=0)
    event_type: EventType
    item_id: str
    source_id: str | None = None
    stage_id: str | None = None
    resource_pool_id: str | None = None
    route_id: str | None = None
    target_id: str | None = None
    priority: int | None = Field(default=None, ge=0)
    attempt: int | None = Field(default=None, ge=0)
    sampled_duration: float | None = Field(default=None, ge=0)
    reason: str | None = None


class StageVisit(ContractModel):
    item_id: str
    stage_id: str
    resource_pool_id: str
    visit_number: int = Field(ge=1)
    queue_entered_at: float
    process_started_at: float
    process_completed_at: float
    sampled_duration: float
    failed: bool
    reworked: bool

    @property
    def waiting_time(self) -> float:
        return self.process_started_at - self.queue_entered_at

    @property
    def processing_time(self) -> float:
        return self.process_completed_at - self.process_started_at


class ItemLifecycle(ContractModel):
    item_id: str
    source_id: str
    priority: int
    created_at: float
    visits: list[StageVisit]
    completed_at: float | None = None
    terminal_failure_at: float | None = None
    completed: bool = False
    terminally_failed: bool = False
    rework_count: int = 0

    @property
    def waiting_time(self) -> float:
        return sum(visit.waiting_time for visit in self.visits)

    @property
    def processing_time(self) -> float:
        return sum(visit.processing_time for visit in self.visits)

    @property
    def cycle_time(self) -> float:
        terminal_time = self.completed_at if self.completed else self.terminal_failure_at
        return 0 if terminal_time is None else terminal_time - self.created_at


class RunMetadata(ContractModel):
    model_name: str
    time_unit: Literal["minutes"] = "minutes"
    seed: int
    started_at: float = 0
    completed_at: float
    deterministic: bool
    run_label: str | None = None


class ObservationMetadata(ContractModel):
    simulation_start: float = 0
    measurement_start: float
    measurement_end: float
    simulation_end: float
    measurement_duration: float
    created_during_window: int
    completed_during_window: int
    terminally_failed_during_window: int
    active_at_measurement_end: int
    excluded_pre_warmup_items: int
    incomplete_at_measurement_end: int


class IntegrityStatus(ContractModel):
    status: Literal["passed"] = "passed"
    checks_run: int = Field(ge=0)


class ResultDetailMetadata(ContractModel):
    mode: Literal["summary", "sampled", "full"]
    total_event_count: int = Field(ge=0)
    included_event_count: int = Field(ge=0)
    selected_item_ids: list[str]


class SystemMetrics(ContractModel):
    created_items: int
    completed_items: int
    terminally_failed_items: int
    throughput: float
    average_waiting_time: float
    average_processing_time: float
    average_cycle_time: float
    p95_cycle_time: float
    maximum_queue_length: int
    sla_attainment: float
    total_rework_count: int
    event_count: int
    arrival_rate: float
    completion_rate: float
    failure_rate: float
    time_weighted_wip: float
    time_weighted_queue_length: float
    flow_efficiency: float


class StageMetrics(ContractModel):
    stage_id: str
    visit_count: int
    completed_processing_count: int
    average_waiting_time: float
    average_processing_time: float
    failure_count: int
    rework_count: int
    maximum_queue_length: int
    time_weighted_queue_length: float
    waiting_time_share: float
    processing_time_share: float


class ResourcePoolMetrics(ContractModel):
    resource_pool_id: str
    capacity: int
    busy_time: float
    utilization: float
    maximum_concurrent_usage: int
    total_requests: int
    busy_capacity_time: float
    available_capacity_time: float
    idle_capacity_proportion: float
    mean_request_wait: float


class SimulationResult(ContractModel):
    schema_version: Literal["0.3.0"] = "0.3.0"
    run: RunMetadata
    observation: ObservationMetadata
    system_metrics: SystemMetrics
    stage_metrics: list[StageMetrics]
    resource_pool_metrics: list[ResourcePoolMetrics]
    integrity: IntegrityStatus
    result_detail: ResultDetailMetadata
    events: list[SimulationEvent]
    items: list[ItemLifecycle] = Field(exclude=True)


class SimulationRequest(ContractModel):
    schema_version: Literal["0.3.0"]
    model: OperationalModel
    run_label: str | None = Field(default=None, min_length=1)
    seed_override: int | None = Field(default=None, ge=0, le=2**63 - 1)
    observation: ObservationConfig = Field(default_factory=ObservationConfig)
    result_detail: ResultDetailConfig = Field(default_factory=ResultDetailConfig)


class HealthResponse(ContractModel):
    status: str
    service: str
