from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostSource:
    key: str
    label: str
    assumption_path: str
    source_metric: str
    unit: str
    formula_label: str
    stage_specific: bool = False
    resource_specific: bool = False
    export_key: str = ""


COST_SOURCE_REGISTRY: dict[str, CostSource] = {
    "resource_provisioning": CostSource(
        "resource_provisioning",
        "Resource provisioning",
        "resourceProvisioning",
        "resourcePool.capacity",
        "currency",
        "capacity × measurement duration × rate",
        resource_specific=True,
        export_key="resource_provisioning_cost",
    ),
    "stage_visit": CostSource(
        "stage_visit",
        "Stage visits",
        "stageVisit",
        "stage.visitCount",
        "currency",
        "visit count × rate",
        stage_specific=True,
        export_key="stage_visit_cost",
    ),
    "queue_holding": CostSource(
        "queue_holding",
        "Queue holding",
        "queueHolding",
        "timeWeightedQueueLength",
        "currency",
        "time-weighted queue × measurement duration × rate",
        stage_specific=True,
        export_key="queue_holding_cost",
    ),
    "wip_holding": CostSource(
        "wip_holding",
        "WIP holding",
        "wipHoldingCostPerItemTimeUnit",
        "system.timeWeightedWip",
        "currency",
        "time-weighted WIP × measurement duration × rate",
        export_key="wip_holding_cost",
    ),
    "sla_violation": CostSource(
        "sla_violation",
        "SLA violations",
        "costPerSlaViolation",
        "system.slaViolationCount",
        "currency",
        "SLA violation count × rate",
        export_key="sla_violation_cost",
    ),
    "terminal_failure": CostSource(
        "terminal_failure",
        "Terminal failures",
        "costPerTerminalFailure",
        "system.terminallyFailedItems",
        "currency",
        "terminal failure count × rate",
        export_key="terminal_failure_cost",
    ),
    "rework": CostSource(
        "rework",
        "Rework",
        "rework",
        "totalReworkCount",
        "currency",
        "rework count × rate",
        stage_specific=True,
        export_key="rework_cost",
    ),
    "completion": CostSource(
        "completion",
        "Completion processing",
        "costPerCompletedItem",
        "system.completedItems",
        "currency",
        "completed item count × rate",
        export_key="completion_cost",
    ),
    "fixed_period": CostSource(
        "fixed_period",
        "Fixed period",
        "fixedCostPerAnalysisPeriod",
        "analysisPeriod",
        "currency",
        "fixed amount once per analysis period",
        export_key="fixed_period_cost",
    ),
}
