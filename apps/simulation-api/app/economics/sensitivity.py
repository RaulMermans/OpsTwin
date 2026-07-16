from __future__ import annotations

from time import perf_counter
from typing import Literal

from app.domain.economics import (
    CostSnapshot,
    EconomicIntegrityStatus,
    EconomicSensitivityExecutionMetadata,
    EconomicSensitivityRequest,
    EconomicSensitivityResult,
    EconomicSensitivityValueResult,
    PairedCostDelta,
)
from app.domain.models import OperationalModel, SimulationResult
from app.domain.repeated import AggregateMetric
from app.domain.sensitivity import MetricResponseCurve, ResponsePoint
from app.economics.aggregation import paired_cost_delta
from app.economics.evaluator import evaluate_cost_snapshot
from app.engine.aggregation import aggregate_metric
from app.sensitivity.analytics import (
    classify_monotonicity,
    finite_differences,
    observed_elasticity,
    threshold_crossings,
)
from app.sensitivity.coordinator import run_sensitivity_analysis

CATEGORY_BY_METRIC = {
    "resourceProvisioningCost": "resource_provisioning",
    "queueHoldingCost": "queue_holding",
    "slaViolationCost": "sla_violation",
    "failureCost": "terminal_failure",
    "reworkCost": "rework",
}


def _metric_value(snapshot: CostSnapshot, metric: str) -> float | None:
    if metric == "recurringOperatingCost":
        return snapshot.recurring_operating_cost
    if metric == "costPerCompletedItem":
        return snapshot.cost_per_completed_item
    category = CATEGORY_BY_METRIC[metric]
    configured = [
        item
        for item in snapshot.components
        if item.category == category and item.status != "not_configured"
    ]
    if not configured or any(item.cost is None for item in configured):
        return None
    return sum(item.cost or 0 for item in configured)


def _validate_integrity(
    request: EconomicSensitivityRequest, result: EconomicSensitivityResult
) -> int:
    baseline = next(item for item in result.values if item.is_baseline_value)
    checks = [
        result.schema_version == "0.7.0",
        result.currency == request.assumptions.currency,
        result.model_time_unit == request.assumptions.model_time_unit,
        result.work_budget == result.operational_sensitivity.work_budget,
        result.execution.ordinary_run_included_event_count == 0,
        result.execution.ordinary_run_retained_event_count == 0,
        result.execution.economic_snapshot_evaluations
        <= result.operational_sensitivity.execution.ordinary_simulation_executions,
        len(result.values) == len(result.operational_sensitivity.values),
        len(result.cost_response_curves) == len(request.cost_metrics),
        [item.parameter_value for item in result.values]
        == result.operational_sensitivity.canonical_values,
        sum(item.is_baseline_value for item in result.values) == 1,
        baseline.status == "valid",
        all(metric in baseline.paired_cost_metrics for metric in request.cost_metrics),
        all(
            abs(baseline.paired_cost_metrics[metric].absolute_delta.mean) <= 1e-9
            for metric in request.cost_metrics
        ),
        all(curve.metric in request.cost_metrics for curve in result.cost_response_curves),
        all(len(curve.points) == len(result.values) for curve in result.cost_response_curves),
        all(curve.direction == "lower" for curve in result.cost_response_curves),
        all(value.undefined_cost_per_completed_item_count >= 0 for value in result.values),
        all(value.status != "valid" or value.cost_metrics for value in result.values),
        all(
            value.failure_category is None or value.status == "economic_failed"
            for value in result.values
        ),
        all(
            0 <= probability <= 1
            for value in result.values
            for probability in value.probability_lower_cost.values()
        ),
        all(curve.unit == request.assumptions.currency for curve in result.cost_response_curves),
        all(
            point.parameter_value in result.operational_sensitivity.canonical_values
            for curve in result.cost_response_curves
            for point in curve.points
        ),
    ]
    if not all(checks):
        raise ValueError("economic sensitivity integrity validation failed")
    return len(checks)


def run_economic_sensitivity(
    request: EconomicSensitivityRequest,
    *,
    record_evaluation_timing: bool = False,
) -> EconomicSensitivityResult:
    snapshots: dict[float, dict[int, CostSnapshot]] = {}
    failures: dict[float, int] = {}
    evaluation_seconds = 0.0
    evaluation_count = 0

    def observe(
        value: float,
        model: OperationalModel,
        run_index: int,
        simulation_result: SimulationResult,
    ) -> None:
        nonlocal evaluation_count, evaluation_seconds
        started = perf_counter()
        try:
            snapshot = evaluate_cost_snapshot(
                simulation_result, model, request.assumptions
            )
            if snapshot.status == "available":
                snapshots.setdefault(value, {})[run_index] = snapshot
                evaluation_count += 1
            else:
                failures[value] = failures.get(value, 0) + 1
        except Exception:
            failures[value] = failures.get(value, 0) + 1
        finally:
            evaluation_seconds += perf_counter() - started

    operational = run_sensitivity_analysis(request.sensitivity, run_observer=observe)
    baseline_value = operational.target.baseline_value
    baseline_snapshots = snapshots.get(baseline_value, {})
    if len(baseline_snapshots) != request.sensitivity.execution.run_count:
        raise ValueError("baseline economic sensitivity evaluation failed")
    values: list[EconomicSensitivityValueResult] = []
    aggregate_by_metric: dict[str, list[tuple[float, float | None]]] = {
        metric: [] for metric in request.cost_metrics
    }
    for operational_value in operational.values:
        value = operational_value.parameter_value
        current = snapshots.get(value, {})
        aggregates: dict[str, AggregateMetric] = {}
        paired: dict[str, PairedCostDelta] = {}
        probabilities: dict[str, float] = {}
        undefined = 0
        for metric in request.cost_metrics:
            current_values = {
                index: metric_value
                for index, snapshot in current.items()
                if (metric_value := _metric_value(snapshot, metric)) is not None
            }
            baseline_values = {
                index: metric_value
                for index, snapshot in baseline_snapshots.items()
                if (metric_value := _metric_value(snapshot, metric)) is not None
            }
            if metric == "costPerCompletedItem":
                undefined = len(current) - len(current_values)
            if current_values:
                aggregates[metric] = aggregate_metric(
                    list(current_values.values()), request.sensitivity.execution.confidence_level
                )
                aggregate_by_metric[metric].append((value, aggregates[metric].mean))
            else:
                aggregate_by_metric[metric].append((value, None))
            if baseline_values and current_values:
                comparison, lower, _, _ = paired_cost_delta(
                    baseline_values,
                    current_values,
                    request.sensitivity.execution.confidence_level,
                )
                paired[metric] = comparison
                probabilities[metric] = lower
        status: Literal["valid", "economic_failed"] = (
            "valid"
            if operational_value.status == "valid" and len(aggregates) == len(request.cost_metrics)
            else "economic_failed"
        )
        values.append(
            EconomicSensitivityValueResult(
                parameter_value=value,
                is_baseline_value=operational_value.is_baseline_value,
                status=status,
                failure_category=None if status == "valid" else "economic_snapshot_failure",
                cost_metrics=aggregates,
                paired_cost_metrics=paired,
                probability_lower_cost=probabilities,
                undefined_cost_per_completed_item_count=undefined,
            )
        )
    curves = []
    for metric in request.cost_metrics:
        analytical = aggregate_by_metric[metric]
        baseline_mean = next(mean for value, mean in analytical if value == baseline_value)
        if baseline_mean is None:
            raise ValueError("baseline economic sensitivity metric is unavailable")
        points = []
        for value_result, (_, mean) in zip(values, analytical, strict=True):
            aggregate = value_result.cost_metrics.get(metric)
            points.append(
                ResponsePoint(
                    parameter_value=value_result.parameter_value,
                    is_baseline_value=value_result.is_baseline_value,
                    status="valid" if aggregate is not None else "failed",
                    mean=mean,
                    confidence_interval_lower=aggregate.confidence_interval.lower
                    if aggregate
                    else None,
                    confidence_interval_upper=aggregate.confidence_interval.upper
                    if aggregate
                    else None,
                    observed_elasticity=(
                        observed_elasticity(
                            baseline_value,
                            baseline_mean,
                            value_result.parameter_value,
                            mean,
                        )
                        if mean is not None and not value_result.is_baseline_value
                        else None
                    ),
                )
            )
        threshold = request.cost_thresholds.get(metric)
        curves.append(
            MetricResponseCurve(
                metric=metric,
                unit=request.assumptions.currency,
                direction="lower",
                points=points,
                finite_differences=finite_differences(
                    metric, request.assumptions.currency, analytical
                ),
                monotonicity=classify_monotonicity(
                    [mean for _, mean in analytical if mean is not None]
                ),
                threshold_crossings=(
                    threshold_crossings(metric, "lessThanOrEqual", threshold, analytical)
                    if threshold is not None
                    else []
                ),
            )
        )
    provisional = EconomicSensitivityResult(
        currency=request.assumptions.currency,
        model_time_unit=request.assumptions.model_time_unit,
        operational_sensitivity=operational,
        values=values,
        cost_response_curves=curves,
        work_budget=operational.work_budget,
        execution=EconomicSensitivityExecutionMetadata(
            economic_snapshot_evaluations=evaluation_count,
            economic_evaluation_seconds=(evaluation_seconds if record_evaluation_timing else 0),
        ),
        integrity=EconomicIntegrityStatus(checks_run=22),
    )
    checks = _validate_integrity(request, provisional)
    return provisional.model_copy(update={"integrity": EconomicIntegrityStatus(checks_run=checks)})
