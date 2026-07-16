from typing import Any

import pytest

from app.domain.models import EventType, OperationalModel, SimulationEvent
from app.engine.integrity import SimulationIntegrityError, validate_simulation
from app.engine.simulator import run_simulation


def resequence(events: list[SimulationEvent]) -> list[SimulationEvent]:
    return [event.model_copy(update={"sequence": index}) for index, event in enumerate(events)]


def test_gm014_valid_run_reports_integrity_checks(
    deterministic_model_data: dict[str, Any],
) -> None:
    result = run_simulation(OperationalModel.model_validate(deterministic_model_data))

    assert result.integrity.status == "passed"
    assert result.integrity.checks_run >= 14


def test_duplicate_completion_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    completion = next(
        event for event in result.events if event.event_type is EventType.ITEM_COMPLETED
    )
    events = resequence([*result.events, completion])

    with pytest.raises(SimulationIntegrityError, match="terminal event"):
        validate_simulation(model, result.items, events)


def test_missing_resource_release_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    events = resequence(
        [
            event
            for index, event in enumerate(result.events)
            if not (event.event_type is EventType.RESOURCE_RELEASED and index > 0)
        ]
    )

    with pytest.raises(SimulationIntegrityError, match="resource acquisition"):
        validate_simulation(model, result.items, events)


def test_capacity_violation_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    first_start_index = next(
        index
        for index, event in enumerate(result.events)
        if event.event_type is EventType.PROCESS_STARTED
    )
    events = list(result.events)
    events.insert(first_start_index + 1, events[first_start_index])

    with pytest.raises(SimulationIntegrityError, match="capacity"):
        validate_simulation(model, result.items, resequence(events))


def test_timestamp_regression_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    events = list(result.events)
    index = next(
        position
        for position in range(1, len(events))
        if events[position - 1].simulation_time > 0
        and events[position].simulation_time > events[position - 1].simulation_time
    )
    events[index] = events[index].model_copy(
        update={"simulation_time": events[index - 1].simulation_time - 0.5}
    )

    with pytest.raises(SimulationIntegrityError, match="timestamps"):
        validate_simulation(model, result.items, events)


def test_lifecycle_count_mismatch_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    items = list(result.items)
    items[0] = items[0].model_copy(update={"completed": False, "completed_at": None})

    with pytest.raises(SimulationIntegrityError, match="terminal event"):
        validate_simulation(model, items, result.events)


def test_sequence_regression_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    events = list(result.events)
    events[1] = events[1].model_copy(update={"sequence": 0})

    with pytest.raises(SimulationIntegrityError, match="sequence"):
        validate_simulation(model, result.items, events)


def test_missing_process_completion_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    events = resequence(
        [
            event
            for event in result.events
            if event.event_type is not EventType.PROCESS_COMPLETED
        ]
    )

    with pytest.raises(SimulationIntegrityError, match="process completion"):
        validate_simulation(model, result.items, events)


def test_invalid_reference_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    events = list(result.events)
    events[0] = events[0].model_copy(update={"source_id": "missing-source"})

    with pytest.raises(SimulationIntegrityError, match="unknown source"):
        validate_simulation(model, result.items, events)


def test_invalid_route_destination_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    events = list(result.events)
    index = next(
        i for i, event in enumerate(events) if event.event_type is EventType.ROUTE_SELECTED
    )
    events[index] = events[index].model_copy(update={"target_id": "missing-stage"})

    with pytest.raises(SimulationIntegrityError, match="invalid destination"):
        validate_simulation(model, result.items, events)


def test_negative_resource_usage_is_rejected(
    deterministic_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    release_index = next(
        index
        for index, event in enumerate(result.events)
        if event.event_type is EventType.RESOURCE_RELEASED
    )
    release = result.events[release_index].model_copy(update={"simulation_time": 0.0})
    events = resequence(
        [release, *result.events[:release_index], *result.events[release_index + 1 :]]
    )

    with pytest.raises(SimulationIntegrityError, match="negative"):
        validate_simulation(model, result.items, events)


def test_rework_mismatch_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    items = list(result.items)
    items[0] = items[0].model_copy(update={"rework_count": 1})

    with pytest.raises(SimulationIntegrityError, match="rework"):
        validate_simulation(model, items, result.events)


def test_stage_visit_mismatch_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    items = list(result.items)
    items[0] = items[0].model_copy(update={"visits": []})

    with pytest.raises(SimulationIntegrityError, match="visit"):
        validate_simulation(model, items, result.events)


def test_negative_duration_is_rejected(deterministic_model_data: dict[str, Any]) -> None:
    model = OperationalModel.model_validate(deterministic_model_data)
    result = run_simulation(model)
    items = list(result.items)
    items[0] = items[0].model_copy(update={"completed_at": items[0].created_at - 1})

    with pytest.raises(SimulationIntegrityError, match="non-negative"):
        validate_simulation(model, items, result.events)
