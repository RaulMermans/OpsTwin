from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from app.domain.comparison import ImprovementResult, PairedMetricResult
from app.domain.models import OperationalModel, ResultDetailConfig, SimulationResult
from app.domain.repeated import AggregateMetric, RunSeed
from app.domain.sensitivity import (
    MetricResponseCurve,
    ResponsePoint,
    SensitivityExecutionMetadata,
    SensitivityFailureEvidence,
    SensitivityIntegrityStatus,
    SensitivityRequest,
    SensitivityResult,
    SensitivityValueResult,
    SensitivityWorkBudget,
)
from app.engine.aggregation import aggregate_metric
from app.engine.seed_schedule import SEED_SCHEDULE_ALGORITHM, seed_schedule
from app.engine.simulator import run_simulation
from app.engine.snapshots import MetricSnapshot, extract_metric_snapshot
from app.scenarios.materializer import canonical_model_hash
from app.scenarios.metrics import METRIC_REGISTRY, compare_paired_metric
from app.sensitivity.analytics import (
    classify_monotonicity,
    finite_differences,
    observed_elasticity,
    threshold_crossings,
)
from app.sensitivity.integrity import validate_sensitivity_integrity
from app.sensitivity.materializer import prepare_sensitivity

MAX_SENSITIVITY_WORK_UNITS = 100_000
SimulationRunner = Callable[..., SimulationResult]
SensitivityRunObserver = Callable[[float, OperationalModel, int, SimulationResult], None]


class SensitivityAnalysisError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SensitivityWorkBudgetError(SensitivityAnalysisError):
    def __init__(self, estimated_work_units: int) -> None:
        super().__init__(
            "sensitivity_work_budget_exceeded",
            "Sensitivity analysis exceeds the synchronous work budget",
        )
        self.estimated_work_units = estimated_work_units
        self.maximum_work_units = MAX_SENSITIVITY_WORK_UNITS


def _require_summary(result: SimulationResult) -> None:
    if (
        result.result_detail.mode != "summary"
        or result.result_detail.included_event_count
        or result.events
    ):
        raise SensitivityAnalysisError(
            "ordinary_run_retention", "Ordinary sensitivity run retained event evidence"
        )


def _threshold(
    request: SensitivityRequest, metric: str
) -> tuple[Literal["greaterThanOrEqual", "lessThanOrEqual"], float] | None:
    values: dict[
        str,
        tuple[
            Literal["greaterThanOrEqual", "lessThanOrEqual"],
            float | None,
        ],
    ] = {
        "slaAttainment": ("greaterThanOrEqual", request.thresholds.minimum_sla_attainment),
        "averageCycleTime": ("lessThanOrEqual", request.thresholds.maximum_average_cycle_time),
        "p95CycleTime": ("lessThanOrEqual", request.thresholds.maximum_p95_cycle_time),
        "timeWeightedQueueLength": (
            "lessThanOrEqual",
            request.thresholds.maximum_time_weighted_queue_length,
        ),
        "terminalFailureRate": (
            "lessThanOrEqual",
            request.thresholds.maximum_terminal_failure_rate,
        ),
    }
    configured = values.get(metric)
    return None if configured is None or configured[1] is None else (configured[0], configured[1])


def run_sensitivity_analysis(
    request: SensitivityRequest,
    *,
    simulation_runner: SimulationRunner = run_simulation,
    run_observer: SensitivityRunObserver | None = None,
) -> SensitivityResult:
    prepared = prepare_sensitivity(request)
    item_count = sum(source.item_count for source in request.baseline_model.sources)
    work_units = item_count * request.execution.run_count * len(prepared.variants)
    if work_units > MAX_SENSITIVITY_WORK_UNITS:
        raise SensitivityWorkBudgetError(work_units)

    seeds = seed_schedule(request.execution.base_seed, request.execution.run_count)
    snapshots: dict[float, dict[int, MetricSnapshot]] = {
        variant.value: {} for variant in prepared.variants
    }
    failures: dict[float, int] = {variant.value: 0 for variant in prepared.variants}
    baseline_value = prepared.target.baseline_value
    ordinary_executions = 0
    for run_index, seed in enumerate(seeds):
        for variant in prepared.variants:
            try:
                run_result = simulation_runner(
                    variant.model,
                    seed_override=seed,
                    observation=request.execution.observation,
                    result_detail=ResultDetailConfig(mode="summary"),
                )
                ordinary_executions += 1
                _require_summary(run_result)
                if run_observer is not None:
                    run_observer(variant.value, variant.model, run_index, run_result)
                snapshots[variant.value][run_index] = extract_metric_snapshot(run_index, run_result)
                del run_result
            except SensitivityAnalysisError:
                raise
            except Exception as error:
                if variant.is_baseline:
                    raise SensitivityAnalysisError(
                        "baseline_execution_failed", "Baseline sensitivity execution failed"
                    ) from error
                failures[variant.value] += 1

    baseline_snapshots = snapshots[baseline_value]
    if len(baseline_snapshots) != request.execution.run_count:
        raise SensitivityAnalysisError(
            "baseline_execution_failed", "Baseline sensitivity execution failed"
        )

    value_results: list[SensitivityValueResult] = []
    for variant in prepared.variants:
        current = snapshots[variant.value]
        paired_indexes = sorted(set(baseline_snapshots) & set(current))
        successful_ratio = len(current) / request.execution.run_count
        paired_ratio = len(paired_indexes) / request.execution.run_count
        valid = (
            successful_ratio >= request.execution.minimum_successful_run_ratio
            and paired_ratio >= request.execution.minimum_paired_run_ratio
        )
        failure = (
            None
            if valid
            else SensitivityFailureEvidence(
                category="paired_ratio_failure",
                message="Value paired-run ratio is below the configured minimum",
            )
        )
        aggregates: dict[str, AggregateMetric] = {
            metric: aggregate_metric(
                [current[index].system[metric] for index in sorted(current)],
                request.execution.confidence_level,
            )
            for metric in request.metrics
        }
        paired: dict[str, PairedMetricResult] = {}
        if valid and not variant.is_baseline:
            for metric in request.metrics:
                comparison = compare_paired_metric(
                    {index: baseline_snapshots[index].system[metric] for index in paired_indexes},
                    {index: current[index].system[metric] for index in paired_indexes},
                    metric=metric,
                    confidence_level=request.execution.confidence_level,
                )
                paired[metric] = PairedMetricResult(
                    metric=metric,
                    absolute_delta=comparison.absolute,
                    relative_delta=comparison.relative,
                    relative_delta_undefined_count=comparison.relative_delta_undefined_count,
                    improvement=ImprovementResult(**comparison.improvement.__dict__),
                )
        value_results.append(
            SensitivityValueResult(
                parameter_value=variant.value,
                is_baseline_value=variant.is_baseline,
                status="valid" if valid else "failed",
                failure=failure,
                model_hash=variant.model_hash,
                successful_run_count=len(current),
                failed_run_count=failures[variant.value],
                successful_run_ratio=successful_ratio,
                paired_run_count=len(paired_indexes),
                paired_run_ratio=paired_ratio,
                system_metrics=aggregates,
                paired_metrics=paired,
            )
        )

    curves: list[MetricResponseCurve] = []
    baseline_result = next(value for value in value_results if value.is_baseline_value)
    for metric in request.metrics:
        baseline_mean = baseline_result.system_metrics[metric].mean
        points: list[ResponsePoint] = []
        analytical_points: list[tuple[float, float | None]] = []
        for value in value_results:
            aggregate = value.system_metrics.get(metric) if value.status == "valid" else None
            mean = aggregate.mean if aggregate else None
            analytical_points.append((value.parameter_value, mean))
            points.append(
                ResponsePoint(
                    parameter_value=value.parameter_value,
                    is_baseline_value=value.is_baseline_value,
                    status=value.status,
                    mean=mean,
                    confidence_interval_lower=aggregate.confidence_interval.lower
                    if aggregate
                    else None,
                    confidence_interval_upper=aggregate.confidence_interval.upper
                    if aggregate
                    else None,
                    observed_elasticity=(
                        observed_elasticity(
                            baseline_value, baseline_mean, value.parameter_value, mean
                        )
                        if mean is not None and not value.is_baseline_value
                        else None
                    ),
                )
            )
        configured_threshold = _threshold(request, metric)
        crossings = []
        if configured_threshold:
            crossings = threshold_crossings(
                metric, configured_threshold[0], configured_threshold[1], analytical_points
            )
        successful_means = [mean for _, mean in analytical_points if mean is not None]
        metadata = METRIC_REGISTRY[metric]
        curves.append(
            MetricResponseCurve(
                metric=metric,
                unit=metadata.unit,
                direction=metadata.direction,
                points=points,
                finite_differences=finite_differences(metric, metadata.unit, analytical_points),
                monotonicity=classify_monotonicity(successful_means),
                threshold_crossings=crossings,
            )
        )

    result = SensitivityResult(
        baseline_model_hash=canonical_model_hash(request.baseline_model),
        target=prepared.target,
        original_values=request.values,
        canonical_values=[variant.value for variant in prepared.variants],
        requested_run_count=request.execution.run_count,
        base_seed=request.execution.base_seed,
        seed_schedule_algorithm=SEED_SCHEDULE_ALGORITHM,
        run_seeds=[RunSeed(run_index=index, seed=seed) for index, seed in enumerate(seeds)],
        confidence_level=request.execution.confidence_level,
        work_budget=SensitivityWorkBudget(
            baseline_item_count=item_count,
            run_count=request.execution.run_count,
            tested_value_count=len(prepared.variants),
            estimated_work_units=work_units,
        ),
        values=value_results,
        response_curves=curves,
        execution=SensitivityExecutionMetadata(ordinary_simulation_executions=ordinary_executions),
        integrity=SensitivityIntegrityStatus(checks_run=18),
    )
    checks = validate_sensitivity_integrity(request, result)
    return result.model_copy(update={"integrity": SensitivityIntegrityStatus(checks_run=checks)})
