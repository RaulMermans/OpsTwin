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

CANONICAL_ITEM_COUNT = 1


class ConstructionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _estimate(estimates: list[ParameterEstimate], parameter_id: str) -> ParameterEstimate:
    match = next((item for item in estimates if item.parameter_id == parameter_id), None)
    if match is None:
        raise ConstructionError("unsupported_parameter", f"{parameter_id} is missing from the estimate set.")  # noqa: E501
    return match


def _numeric(estimates: list[ParameterEstimate], parameter_id: str) -> float:
    match = _estimate(estimates, parameter_id)
    if not match.consumed_by_model:
        raise ConstructionError("unsupported_parameter", f"{parameter_id} is diagnostic and cannot bind the model.")  # noqa: E501
    if not isinstance(match.value, int | float) or isinstance(match.value, bool):
        raise ConstructionError("missing_assumptions", f"{parameter_id} has no numeric value.")
    return float(match.value)


def _integer_capacity(estimates: list[ParameterEstimate], parameter_id: str) -> int:
    value = _numeric(estimates, parameter_id)
    if value != int(value):
        raise ConstructionError(
            "contract_validation_failure",
            f"{parameter_id} must be a whole number of servers.",
        )
    return int(value)


def _routing_options(probability: float) -> list[RouteOption]:
    if probability < 0 or probability > 1:
        raise ConstructionError("contract_validation_failure", "Routing probabilities must lie in [0, 1].")  # noqa: E501
    options: list[RouteOption] = []
    if probability > 0:
        options.append(RouteOption(target_type="stage", target_id="resolution", probability=probability))  # noqa: E501
    if probability < 1:
        options.append(RouteOption(target_type="completion", probability=1 - probability))
    if not options:
        raise ConstructionError("unsupported_parameter", "Routing probability produced no supported route.")  # noqa: E501
    return options


def construct_model(
    estimates: list[ParameterEstimate],
    seed: int,
    item_count: int = CANONICAL_ITEM_COUNT,
    sla_minutes: float = 240.0,
) -> OperationalModel:
    mean_ia = _numeric(estimates, "arrival.mean_interarrival_time")
    triage_mean = _numeric(estimates, "triage.processing_time.mean")
    resolution_mean = _numeric(estimates, "resolution.processing_time.mean")
    routing = _numeric(estimates, "routing.triage_to_resolution")
    triage_cap = _integer_capacity(estimates, "resource.triage-team.capacity")
    resolution_cap = _integer_capacity(estimates, "resource.resolution-team.capacity")
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
                options=_routing_options(routing),
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
    payload["sources"] = [
        {key: value for key, value in source.items() if key != "itemCount"}
        for source in payload.get("sources") or []
    ]
    return sha256_canonical({"engine": ENGINE_VERSION, "model": payload})
