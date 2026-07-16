from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.repeated import AggregateMetric, ConfidenceLevel
from app.engine.aggregation import aggregate_metric

FLOAT_COMPARISON_TOLERANCE = 1e-9
MetricQualityDirection = Literal["higher", "lower", "contextual"]


@dataclass(frozen=True)
class MetricMetadata:
    key: str
    label: str
    unit: str
    direction: MetricQualityDirection
    relative_delta_supported: bool
    guardrail_operators: tuple[str, ...]
    objective_eligible: bool


def _metric(
    key: str,
    label: str,
    unit: str,
    direction: MetricQualityDirection,
    *,
    objective: bool = True,
    guardrails: tuple[str, ...] = ("lessThanOrEqual", "greaterThanOrEqual"),
) -> MetricMetadata:
    return MetricMetadata(key, label, unit, direction, True, guardrails, objective)


METRIC_REGISTRY: dict[str, MetricMetadata] = {
    "slaAttainment": _metric("slaAttainment", "SLA attainment", "ratio", "higher"),
    "completionRate": _metric("completionRate", "Completion rate", "items/minute", "higher"),
    "flowEfficiency": _metric("flowEfficiency", "Flow efficiency", "ratio", "higher"),
    "averageWaitingTime": _metric("averageWaitingTime", "Average waiting time", "minutes", "lower"),
    "averageCycleTime": _metric("averageCycleTime", "Average cycle time", "minutes", "lower"),
    "p95CycleTime": _metric("p95CycleTime", "p95 cycle time", "minutes", "lower"),
    "terminalFailureRate": _metric(
        "terminalFailureRate", "Terminal failure rate", "ratio", "lower"
    ),
    "timeWeightedWip": _metric("timeWeightedWip", "Time-weighted WIP", "items", "lower"),
    "timeWeightedQueueLength": _metric(
        "timeWeightedQueueLength", "Time-weighted queue", "items", "lower"
    ),
    "totalReworkCount": _metric("totalReworkCount", "Total rework", "count", "lower"),
    "resourcePoolUtilization": _metric(
        "resourcePoolUtilization",
        "Resource-pool utilization",
        "ratio",
        "contextual",
        objective=False,
        guardrails=("lessThanOrEqual",),
    ),
}


@dataclass(frozen=True)
class ImprovementCounts:
    improved_count: int
    degraded_count: int
    tied_count: int
    probability_of_improvement: float
    probability_of_degradation: float
    probability_of_tie: float
    valid_paired_run_count: int


@dataclass(frozen=True)
class PairedMetricComparison:
    metric: str
    paired_run_indexes: list[int]
    deltas: list[float]
    relative_deltas: list[float | None]
    absolute: AggregateMetric
    relative: AggregateMetric | None
    relative_delta_undefined_count: int
    improvement: ImprovementCounts


@dataclass(frozen=True)
class RiskComparison:
    metric: str
    threshold: float
    baseline_probability: float
    scenario_probability: float
    probability_point_change: float
    relative_change: float | None
    baseline_only_violates: int
    scenario_only_violates: int
    both_violate: int
    neither_violates: int
    paired_run_count: int


def compare_paired_metric(
    baseline: dict[int, float],
    scenario: dict[int, float],
    *,
    metric: str,
    confidence_level: ConfidenceLevel,
) -> PairedMetricComparison:
    metadata = METRIC_REGISTRY[metric]
    indexes = sorted(set(baseline) & set(scenario))
    if not indexes:
        raise ValueError("paired metric comparison requires a successful intersection")
    deltas = [scenario[index] - baseline[index] for index in indexes]
    relative_deltas = [
        None
        if baseline[index] == 0
        else (scenario[index] - baseline[index]) / abs(baseline[index])
        for index in indexes
    ]
    relative_values = [value for value in relative_deltas if value is not None]
    improved = degraded = tied = 0
    for delta in deltas:
        if abs(delta) <= FLOAT_COMPARISON_TOLERANCE:
            tied += 1
        elif (metadata.direction == "higher" and delta > 0) or (
            metadata.direction == "lower" and delta < 0
        ):
            improved += 1
        else:
            degraded += 1
    count = len(indexes)
    return PairedMetricComparison(
        metric=metric,
        paired_run_indexes=indexes,
        deltas=deltas,
        relative_deltas=relative_deltas,
        absolute=aggregate_metric(deltas, confidence_level),
        relative=(
            aggregate_metric(relative_values, confidence_level)
            if relative_values
            else None
        ),
        relative_delta_undefined_count=count - len(relative_values),
        improvement=ImprovementCounts(
            improved_count=improved,
            degraded_count=degraded,
            tied_count=tied,
            probability_of_improvement=improved / count,
            probability_of_degradation=degraded / count,
            probability_of_tie=tied / count,
            valid_paired_run_count=count,
        ),
    )


def compare_threshold_risk(
    baseline: dict[int, float],
    scenario: dict[int, float],
    *,
    metric: str,
    operator: Literal["above", "below"],
    threshold: float,
) -> RiskComparison:
    indexes = sorted(set(baseline) & set(scenario))
    if not indexes:
        raise ValueError("risk comparison requires a successful intersection")

    def violates(value: float) -> bool:
        return value > threshold if operator == "above" else value < threshold

    baseline_only = scenario_only = both = neither = 0
    for index in indexes:
        baseline_violation = violates(baseline[index])
        scenario_violation = violates(scenario[index])
        if baseline_violation and scenario_violation:
            both += 1
        elif baseline_violation:
            baseline_only += 1
        elif scenario_violation:
            scenario_only += 1
        else:
            neither += 1
    count = len(indexes)
    baseline_probability = (baseline_only + both) / count
    scenario_probability = (scenario_only + both) / count
    change = scenario_probability - baseline_probability
    return RiskComparison(
        metric=metric,
        threshold=threshold,
        baseline_probability=baseline_probability,
        scenario_probability=scenario_probability,
        probability_point_change=change,
        relative_change=(
            None if baseline_probability == 0 else change / baseline_probability
        ),
        baseline_only_violates=baseline_only,
        scenario_only_violates=scenario_only,
        both_violate=both,
        neither_violates=neither,
        paired_run_count=count,
    )
