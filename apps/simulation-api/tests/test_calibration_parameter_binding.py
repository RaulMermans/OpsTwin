from __future__ import annotations

from copy import deepcopy

from app.calibration.construct import construct_model
from app.calibration.contracts import ParameterEstimate
from app.calibration.histories import approved_capacity_and_service, default_mapping
from app.domain.models import ResultDetailConfig
from app.engine.simulator import run_simulation


def _estimate(parameter_id: str, path: str, value: float, consumed: bool = True) -> ParameterEstimate:  # noqa: E501
    return ParameterEstimate(
        parameter_id=parameter_id,
        target_model_path=path,
        parameter_type="number",
        value=value,
        unit="minutes",
        estimation_method="test",
        evidence_class="synthetic",
        identifiability_status="identifiable",
        sample_size=10,
        consumed_by_model=consumed,
    )


def _material(**overrides: float) -> list[ParameterEstimate]:
    values = {
        "arrival.mean_interarrival_time": ("sources[0].arrival.meanInterarrivalTime", 30.0),
        "triage.processing_time.mean": ("stages[triage].processingTime.mean", 8.0),
        "resolution.processing_time.mean": ("stages[resolution].processingTime.mean", 12.0),
        "resource.triage-team.capacity": ("resourcePools[triage-team].capacity", 4.0),
        "resource.resolution-team.capacity": ("resourcePools[resolution-team].capacity", 6.0),
        "routing.triage_to_resolution": ("routes[triage-success].options", 1.0),
    }
    values.update({key: (values[key][0], overrides[key]) for key in overrides})
    return [_estimate(key, path, value) for key, (path, value) in values.items()]


def test_each_material_estimate_binds_the_matching_model_field() -> None:
    base = construct_model(_material(), seed=1)
    arrival = construct_model(_material(**{"arrival.mean_interarrival_time": 45.0}), seed=1)
    assert arrival.sources[0].arrival.mean_interarrival_time == 45.0  # type: ignore[union-attr]
    assert arrival.sources[0].arrival.mean_interarrival_time != base.sources[0].arrival.mean_interarrival_time  # type: ignore[union-attr]  # noqa: E501
    triage = construct_model(_material(**{"triage.processing_time.mean": 20.0}), seed=1)
    assert triage.stages[0].processing_time.mean == 20.0  # type: ignore[union-attr]
    resolution = construct_model(_material(**{"resolution.processing_time.mean": 40.0}), seed=1)
    assert resolution.stages[1].processing_time.mean == 40.0  # type: ignore[union-attr]
    cap = construct_model(_material(**{"resource.triage-team.capacity": 9.0}), seed=1)
    assert cap.resource_pools[0].capacity == 9
    routing = construct_model(_material(**{"routing.triage_to_resolution": 0.7}), seed=1)
    options = routing.routes[0].options
    resolution_p = next(option.probability for option in options if option.target_id == "resolution")  # noqa: E501
    assert abs(resolution_p - 0.7) < 1e-12
    assert abs(sum(option.probability for option in options) - 1.0) < 1e-12


def test_missing_resolution_mean_is_not_replaced_by_triage() -> None:
    estimates = [item for item in _material() if item.parameter_id != "resolution.processing_time.mean"]  # noqa: E501
    try:
        construct_model(estimates, seed=1)
    except Exception as error:
        assert "resolution.processing_time.mean" in str(error)
    else:
        raise AssertionError("resolution must not silently inherit triage duration")


def test_routing_70_30_is_reflected_in_simulation() -> None:
    model = construct_model(_material(**{"routing.triage_to_resolution": 0.7}), seed=7, item_count=400)  # noqa: E501
    result = run_simulation(model, seed_override=11, result_detail=ResultDetailConfig(mode="summary"))  # noqa: E501
    completed = [item for item in result.items if item.completed]
    with_resolution = sum(any(visit.stage_id == "resolution" for visit in item.visits) for item in completed)  # noqa: E501
    share = with_resolution / len(completed)
    assert 0.62 <= share <= 0.78


def test_rework_and_mix_are_not_consumed() -> None:
    mapping = default_mapping(reviewed=True)
    assert mapping["reviewed"] is True
    assumptions = approved_capacity_and_service()
    assert all(item["affectedParameter"] == item["assumptionId"] for item in assumptions)
    leftover = deepcopy(_material())
    leftover.append(
        _estimate("rework.probability", "stages[resolution].failure.probability", 0.9, consumed=False)  # noqa: E501
    )
    model = construct_model(leftover, seed=1)
    assert all(stage.failure is None for stage in model.stages)
