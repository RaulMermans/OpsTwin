import hashlib

from app.domain.models import (
    OperationalModel,
    ResultDetailConfig,
    ResultDetailMetadata,
    SimulationEvent,
)


def select_item_ids(
    model: OperationalModel, seed: int, config: ResultDetailConfig
) -> list[str]:
    """Select predictable item IDs before execution without simulation RNG access."""
    if config.mode != "sampled":
        return []
    item_ids = [
        f"{source.id}-item-{item_number}"
        for source in model.sources
        for item_number in range(1, source.item_count + 1)
    ]
    return sorted(
        item_ids,
        key=lambda item_id: (
            hashlib.sha256(f"{seed}:{item_id}".encode()).hexdigest(),
            item_id,
        ),
    )[: config.sampled_item_limit or 0]


def build_result_detail_metadata(
    events: list[SimulationEvent],
    total_event_count: int,
    selected_item_ids: list[str],
    config: ResultDetailConfig,
) -> ResultDetailMetadata:
    return ResultDetailMetadata(
        mode=config.mode,
        total_event_count=total_event_count,
        included_event_count=len(events),
        selected_item_ids=selected_item_ids,
    )
