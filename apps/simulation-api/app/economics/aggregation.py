from __future__ import annotations

from app.domain.economics import CostAggregate, CostSnapshot, PairedCostDelta
from app.engine.aggregation import aggregate_metric


def component_key(category: str, entity_id: str | None) -> str:
    return f"{category}:{entity_id or 'global'}"


def aggregate_cost_snapshots(
    snapshots: list[CostSnapshot], confidence_level: float
) -> CostAggregate:
    available = [item for item in snapshots if item.recurring_operating_cost is not None]
    if not available:
        raise ValueError("economic aggregation requires available recurring costs")
    component_values: dict[str, list[float]] = {}
    for snapshot in available:
        for component in snapshot.components:
            if component.cost is not None:
                component_values.setdefault(
                    component_key(component.category, component.entity_id), []
                ).append(component.cost)
    per_completion = [
        item.cost_per_completed_item
        for item in available
        if item.cost_per_completed_item is not None
    ]
    recurring_values = [
        item.recurring_operating_cost
        for item in available
        if item.recurring_operating_cost is not None
    ]
    return CostAggregate(
        recurring_operating_cost=aggregate_metric(recurring_values, confidence_level),
        cost_per_completed_item=(
            aggregate_metric(per_completion, confidence_level) if per_completion else None
        ),
        undefined_cost_per_completed_item_count=len(available) - len(per_completion),
        component_costs={
            key: aggregate_metric(values, confidence_level)
            for key, values in sorted(component_values.items())
        },
    )


def paired_cost_delta(
    baseline: dict[int, float], scenario: dict[int, float], confidence_level: float
) -> tuple[PairedCostDelta, float, float, float]:
    indexes = sorted(set(baseline) & set(scenario))
    if not indexes:
        raise ValueError("economic pairing requires a successful intersection")
    deltas = [scenario[index] - baseline[index] for index in indexes]
    relatives = [
        None if baseline[index] == 0 else (scenario[index] - baseline[index]) / abs(baseline[index])
        for index in indexes
    ]
    defined = [value for value in relatives if value is not None]
    tolerance = 1e-9
    lower = sum(value < -tolerance for value in deltas)
    higher = sum(value > tolerance for value in deltas)
    tied = len(deltas) - lower - higher
    return (
        PairedCostDelta(
            absolute_delta=aggregate_metric(deltas, confidence_level),
            relative_delta=aggregate_metric(defined, confidence_level) if defined else None,
            relative_delta_undefined_count=len(deltas) - len(defined),
        ),
        lower / len(deltas),
        higher / len(deltas),
        tied / len(deltas),
    )


def paired_component_deltas(
    baseline: dict[int, CostSnapshot],
    scenario: dict[int, CostSnapshot],
    confidence_level: float,
) -> dict[str, PairedCostDelta]:
    indexes = sorted(set(baseline) & set(scenario))
    baseline_maps = {
        index: {
            component_key(item.category, item.entity_id): item.cost
            for item in baseline[index].components
            if item.cost is not None
        }
        for index in indexes
    }
    scenario_maps = {
        index: {
            component_key(item.category, item.entity_id): item.cost
            for item in scenario[index].components
            if item.cost is not None
        }
        for index in indexes
    }
    keys = sorted(
        set.intersection(
            *(set(baseline_maps[index]) & set(scenario_maps[index]) for index in indexes)
        )
    )
    return {
        key: paired_cost_delta(
            {index: float(baseline_maps[index][key]) for index in indexes},
            {index: float(scenario_maps[index][key]) for index in indexes},
            confidence_level,
        )[0]
        for key in keys
    }
