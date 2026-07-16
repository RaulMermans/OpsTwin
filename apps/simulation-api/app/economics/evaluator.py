from __future__ import annotations

from collections.abc import Iterable

from app.domain.economics import (
    CostComponent,
    CostSnapshot,
    CostSnapshotIntegrity,
    EconomicAssumptions,
)
from app.domain.models import OperationalModel, SimulationResult
from app.economics.registry import COST_SOURCE_REGISTRY


def _component(
    category: str,
    *,
    entity_id: str | None,
    assumption: str | None,
    metric: str | None,
    quantity: float | None,
    duration: float | None,
    rate: float | None,
    configured: bool,
    reason: str | None = None,
) -> CostComponent:
    source = COST_SOURCE_REGISTRY[category]
    if not configured:
        return CostComponent(
            category=category,
            entity_id=entity_id,
            formula_label=source.formula_label,
            cost=0,
            status="not_configured",
        )
    if reason is not None or quantity is None or rate is None:
        return CostComponent(
            category=category,
            entity_id=entity_id,
            source_assumption=assumption,
            source_metric=metric,
            source_quantity=quantity,
            duration=duration,
            rate=rate,
            formula_label=source.formula_label,
            status="unavailable",
            reason=reason or "Configured operational source metric is unavailable",
        )
    cost = quantity * rate * (duration if duration is not None else 1)
    return CostComponent(
        category=category,
        entity_id=entity_id,
        source_assumption=assumption,
        source_metric=metric,
        source_quantity=quantity,
        duration=duration,
        rate=rate,
        formula_label=source.formula_label,
        cost=cost,
        status="available",
    )


def _one_or_placeholder(category: str, items: Iterable[CostComponent]) -> list[CostComponent]:
    values = list(items)
    return values or [
        _component(
            category,
            entity_id=None,
            assumption=None,
            metric=None,
            quantity=None,
            duration=None,
            rate=None,
            configured=False,
        )
    ]


def evaluate_cost_snapshot(
    result: SimulationResult,
    model: OperationalModel,
    assumptions: EconomicAssumptions,
) -> CostSnapshot:
    assumptions.validate_entities(
        {item.id for item in model.resource_pools}, {item.id for item in model.stages}
    )
    duration = result.observation.measurement_duration
    stage_metrics = {item.stage_id: item for item in result.stage_metrics}
    resources = {item.id: item for item in model.resource_pools}
    components: list[CostComponent] = []
    components.extend(
        _one_or_placeholder(
            "resource_provisioning",
            (
                _component(
                    "resource_provisioning",
                    entity_id=item.resource_pool_id,
                    assumption="costPerCapacityTimeUnit",
                    metric="resourcePool.capacity",
                    quantity=float(resources[item.resource_pool_id].capacity),
                    duration=duration,
                    rate=item.cost_per_capacity_time_unit,
                    configured=True,
                )
                for item in assumptions.resource_provisioning
            ),
        )
    )
    components.extend(
        _one_or_placeholder(
            "stage_visit",
            (
                _component(
                    "stage_visit",
                    entity_id=item.stage_id,
                    assumption="costPerVisit",
                    metric="stage.visitCount",
                    quantity=float(stage_metrics[item.stage_id].visit_count)
                    if item.stage_id in stage_metrics
                    else None,
                    duration=None,
                    rate=item.cost_per_visit,
                    configured=True,
                    reason=None
                    if item.stage_id in stage_metrics
                    else "Configured stage visit evidence is unavailable",
                )
                for item in assumptions.stage_visit
            ),
        )
    )
    components.extend(
        _one_or_placeholder(
            "queue_holding",
            (
                _component(
                    "queue_holding",
                    entity_id=item.stage_id,
                    assumption="costPerItemTimeUnit",
                    metric="stage.timeWeightedQueueLength"
                    if item.stage_id
                    else "system.timeWeightedQueueLength",
                    quantity=(
                        float(stage_metrics[item.stage_id].time_weighted_queue_length)
                        if item.stage_id in stage_metrics
                        else None
                    )
                    if item.stage_id
                    else result.system_metrics.time_weighted_queue_length,
                    duration=duration,
                    rate=item.cost_per_item_time_unit,
                    configured=True,
                    reason=(
                        "Configured stage queue evidence is unavailable"
                        if item.stage_id and item.stage_id not in stage_metrics
                        else None
                    ),
                )
                for item in assumptions.queue_holding
            ),
        )
    )
    system = result.system_metrics
    components.append(
        _component(
            "wip_holding",
            entity_id=None,
            assumption="wipHoldingCostPerItemTimeUnit",
            metric="system.timeWeightedWip",
            quantity=system.time_weighted_wip,
            duration=duration,
            rate=assumptions.wip_holding_cost_per_item_time_unit,
            configured=assumptions.wip_holding_cost_per_item_time_unit is not None,
        )
    )
    terminal_count = system.completed_items + system.terminally_failed_items
    violations = max(0, terminal_count - round(system.sla_attainment * terminal_count))
    components.append(
        _component(
            "sla_violation",
            entity_id=None,
            assumption="costPerSlaViolation",
            metric="system.slaViolationCount",
            quantity=float(violations),
            duration=None,
            rate=assumptions.cost_per_sla_violation,
            configured=assumptions.cost_per_sla_violation is not None,
        )
    )
    components.append(
        _component(
            "terminal_failure",
            entity_id=None,
            assumption="costPerTerminalFailure",
            metric="system.terminallyFailedItems",
            quantity=float(system.terminally_failed_items),
            duration=None,
            rate=assumptions.cost_per_terminal_failure,
            configured=assumptions.cost_per_terminal_failure is not None,
        )
    )
    components.extend(
        _one_or_placeholder(
            "rework",
            (
                _component(
                    "rework",
                    entity_id=item.stage_id,
                    assumption="costPerRework",
                    metric="stage.reworkCount" if item.stage_id else "system.totalReworkCount",
                    quantity=(
                        float(stage_metrics[item.stage_id].rework_count)
                        if item.stage_id in stage_metrics
                        else None
                    )
                    if item.stage_id
                    else float(system.total_rework_count),
                    duration=None,
                    rate=item.cost_per_rework,
                    configured=True,
                    reason="Configured stage rework evidence is unavailable"
                    if item.stage_id and item.stage_id not in stage_metrics
                    else None,
                )
                for item in assumptions.rework
            ),
        )
    )
    components.append(
        _component(
            "completion",
            entity_id=None,
            assumption="costPerCompletedItem",
            metric="system.completedItems",
            quantity=float(system.completed_items),
            duration=None,
            rate=assumptions.cost_per_completed_item,
            configured=assumptions.cost_per_completed_item is not None,
        )
    )
    components.append(
        _component(
            "fixed_period",
            entity_id=None,
            assumption="fixedCostPerAnalysisPeriod",
            metric="analysisPeriod",
            quantity=1.0,
            duration=None,
            rate=assumptions.fixed_cost_per_analysis_period,
            configured=assumptions.fixed_cost_per_analysis_period is not None,
        )
    )
    configured = [item for item in components if item.status != "not_configured"]
    missing = [
        f"{item.category}:{item.entity_id or 'global'}"
        for item in configured
        if item.status == "unavailable"
    ]
    recurring = None if missing else sum(item.cost or 0 for item in configured)
    cost_per_completion = (
        recurring / system.completed_items
        if recurring is not None and system.completed_items > 0
        else None
    )
    reconciles = (
        recurring is None or abs(recurring - sum(item.cost or 0 for item in configured)) <= 1e-9
    )
    if not reconciles:
        raise ValueError("economic component reconciliation failed")
    return CostSnapshot(
        currency=assumptions.currency,
        model_time_unit=assumptions.model_time_unit,
        measurement_duration=duration,
        components=components,
        status="unavailable" if missing else "available",
        recurring_operating_cost=recurring,
        completed_item_count=system.completed_items,
        cost_per_completed_item=cost_per_completion,
        configured_component_count=len(configured),
        available_component_count=sum(item.status == "available" for item in configured),
        missing_components=missing,
        integrity=CostSnapshotIntegrity(checks_run=8),
    )
