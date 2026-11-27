from __future__ import annotations

from app.calibration.contracts import ENGINE_VERSION, ParameterEstimate
from app.calibration.snapshot import sha256_canonical
from app.domain.models import (
    ExponentialDistribution,
    OperationalModel,
    PoissonArrival,
    ResourcePoolConfig,
    RouteConfig,
    RouteOption,
    RunConfig,
    SlaRule,
    SourceConfig,
    StageConfig,
)


class ConstructionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _numeric(estimates: list[ParameterEstimate], parameter_id: str) -> float:
    match = next((item for item in estimates if item.parameter_id == parameter_id), None)
    if match is None or not isinstance(match.value, int | float):
        raise ConstructionError("missing_assumptions", f"{parameter_id} has no numeric value.")
    return float(match.value)


def construct_model(
    estimates: list[ParameterEstimate],
    seed: int,
    item_count: int,
    sla_minutes: float = 240.0,
) -> OperationalModel:
    mean_ia = _numeric(estimates, "arrival.mean_interarrival_time")
    triage_mean = _numeric(estimates, "triage.processing_time.mean")
    try:
        resolution_mean = _numeric(estimates, "resolution.processing_time.mean")
    except ConstructionError:
        resolution_mean = triage_mean
    triage_cap = int(_numeric(estimates, "resource.triage-team.capacity"))
    resolution_cap = int(_numeric(estimates, "resource.resolution-team.capacity"))
    if mean_ia <= 0 or triage_mean <= 0 or resolution_mean <= 0:
        raise ConstructionError("contract_validation_failure", "Durations and interarrival must be positive.")  # noqa: E501
    if triage_cap < 1 or resolution_cap < 1:
        raise ConstructionError("contract_validation_failure", "Capacity must be at least 1.")
    if item_count < 1:
        raise ConstructionError("contract_validation_failure", "itemCount must be at least 1.")
    return OperationalModel(
        schema_version="0.2.0",
        name="Calibrated support-triage-resolution",
        time_unit="minutes",
        run_config=RunConfig(seed=seed),
        sources=[
            SourceConfig(
                id="arrivals",
                name="Calibrated arrivals",
                item_count=item_count,
                initial_arrival_time=0,
                priority=1,
                first_stage_id="triage",
                arrival=PoissonArrival(type="poisson", mean_interarrival_time=mean_ia),
            )
        ],
        resource_pools=[
            ResourcePoolConfig(id="triage-team", name="Triage team", capacity=triage_cap),
            ResourcePoolConfig(id="resolution-team", name="Resolution team", capacity=resolution_cap),  # noqa: E501
        ],
        stages=[
            StageConfig(
                id="triage",
                name="Triage",
                resource_pool_id="triage-team",
                processing_time=ExponentialDistribution(type="exponential", mean=triage_mean),
                queue_policy="fifo",
            ),
            StageConfig(
                id="resolution",
                name="Resolution",
                resource_pool_id="resolution-team",
                processing_time=ExponentialDistribution(type="exponential", mean=resolution_mean),
                queue_policy="fifo",
            ),
        ],
        routes=[
            RouteConfig(
                id="triage-success",
                kind="success",
                from_stage_id="triage",
                options=[
                    RouteOption(target_type="stage", target_id="resolution", probability=1),
                ],
            ),
            RouteConfig(
                id="resolution-success",
                kind="success",
                from_stage_id="resolution",
                options=[RouteOption(target_type="completion", probability=1)],
            ),
        ],
        sla_rules=[SlaRule(id="resolution-sla", target_duration=sla_minutes)],
    )


def model_fingerprint(model: OperationalModel) -> str:
    payload = model.model_dump(by_alias=True, exclude={"run_config": {"seed"}})
    return sha256_canonical({"engine": ENGINE_VERSION, "model": payload})
