import hashlib
from typing import Any

from app.domain.models import OperationalModel, ResultDetailConfig
from app.engine.simulator import run_simulation


def stable_selection(seed: int, item_ids: list[str], limit: int) -> list[str]:
    ranked = sorted(
        item_ids,
        key=lambda item_id: (hashlib.sha256(f"{seed}:{item_id}".encode()).hexdigest(), item_id),
    )
    return ranked[:limit]


def test_gm017_detail_modes_preserve_metrics_and_bound_events(
    support_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(support_model_data)
    summary = run_simulation(model, result_detail=ResultDetailConfig(mode="summary"))
    sampled = run_simulation(
        model,
        result_detail=ResultDetailConfig(mode="sampled", sampled_item_limit=2),
    )
    full = run_simulation(model, result_detail=ResultDetailConfig(mode="full"))

    assert summary.system_metrics == sampled.system_metrics == full.system_metrics
    assert summary.stage_metrics == sampled.stage_metrics == full.stage_metrics
    assert (
        summary.resource_pool_metrics
        == sampled.resource_pool_metrics
        == full.resource_pool_metrics
    )
    assert summary.observation == sampled.observation == full.observation
    assert summary.integrity == sampled.integrity == full.integrity

    total = full.result_detail.total_event_count
    assert total == full.result_detail.included_event_count == len(full.events)
    assert summary.events == []
    assert summary.result_detail.included_event_count == 0

    expected_ids = stable_selection(full.run.seed, [item.item_id for item in full.items], 2)
    assert sampled.result_detail.selected_item_ids == expected_ids
    assert {event.item_id for event in sampled.events} == set(expected_ids)
    assert sampled.result_detail.included_event_count == len(sampled.events)
    assert sampled.result_detail.total_event_count == total


def test_event_sampling_does_not_change_subsequent_full_run(
    support_model_data: dict[str, Any],
) -> None:
    model = OperationalModel.model_validate(support_model_data)
    before = run_simulation(model, result_detail=ResultDetailConfig(mode="full"))
    run_simulation(
        model,
        result_detail=ResultDetailConfig(mode="sampled", sampled_item_limit=3),
    )
    after = run_simulation(model, result_detail=ResultDetailConfig(mode="full"))

    assert before == after
