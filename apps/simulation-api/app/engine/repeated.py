import math
from collections.abc import Callable

from pydantic import ValidationError

from app.domain.models import (
    ResultDetailConfig,
    SimulationResult,
)
from app.domain.repeated import (
    AggregateMetric,
    ConvergenceCheckpoint,
    FailedRunEvidence,
    FailureCategory,
    RepeatedExecutionMetadata,
    RepeatedIntegrityStatus,
    RepeatedSimulationRequest,
    RepeatedSimulationResult,
    RepresentativeRunResult,
    ResourceMetricAggregates,
    RunningMeanPoint,
    RunSeed,
    StageMetricAggregates,
)
from app.engine.aggregation import (
    RepresentativeCandidate,
    aggregate_metric,
    evaluate_risks,
    select_representative,
)
from app.engine.integrity import SimulationIntegrityError
from app.engine.seed_schedule import SEED_SCHEDULE_ALGORITHM, seed_schedule
from app.engine.simulator import run_simulation
from app.engine.snapshots import MetricSnapshot, extract_metric_snapshot

SimulationRunner = Callable[..., SimulationResult]


class SerializationFailure(RuntimeError):
    """Safe internal marker for a per-run serialization failure."""


class RepeatedSimulationError(RuntimeError):
    """Structured failure raised when a repeated batch cannot be returned safely."""

    def __init__(
        self,
        code: str,
        message: str,
        failed_runs: list[FailedRunEvidence] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.failed_runs = failed_runs or []


def classify_run_failure(
    run_index: int, seed: int, error: Exception
) -> FailedRunEvidence:
    category: FailureCategory
    if isinstance(error, ValidationError):
        category = "domain_validation"
        message = "Simulation input validation failed"
    elif isinstance(error, SimulationIntegrityError):
        category = "integrity_failure"
        message = "Simulation integrity validation failed"
    elif isinstance(error, SerializationFailure):
        category = "serialization_failure"
        message = "Simulation result serialization failed"
    else:
        category = "execution_failure"
        message = "Simulation execution failed"
    return FailedRunEvidence(
        run_index=run_index,
        seed=seed,
        category=category,
        message=message,
    )


def aggregate_snapshot_groups(
    snapshots: list[MetricSnapshot], confidence_level: float
) -> tuple[
    dict[str, AggregateMetric],
    list[StageMetricAggregates],
    list[ResourceMetricAggregates],
]:
    level = confidence_level
    system = {
        metric: aggregate_metric(
            [snapshot.system[metric] for snapshot in snapshots], level
        )
        for metric in snapshots[0].system
    }
    expected_stages = list(snapshots[0].stages)
    expected_resources = list(snapshots[0].resources)
    if any(list(snapshot.stages) != expected_stages for snapshot in snapshots):
        raise RepeatedSimulationError(
            "stage_metric_mismatch", "Stage metric identifiers differ across runs"
        )
    if any(list(snapshot.resources) != expected_resources for snapshot in snapshots):
        raise RepeatedSimulationError(
            "resource_metric_mismatch", "Resource metric identifiers differ across runs"
        )
    stages = [
        StageMetricAggregates(
            stage_id=stage_id,
            metrics={
                metric: aggregate_metric(
                    [snapshot.stages[stage_id][metric] for snapshot in snapshots],
                    level,
                )
                for metric in snapshots[0].stages[stage_id]
            },
        )
        for stage_id in expected_stages
    ]
    resources = [
        ResourceMetricAggregates(
            resource_pool_id=resource_id,
            metrics={
                metric: aggregate_metric(
                    [snapshot.resources[resource_id][metric] for snapshot in snapshots],
                    level,
                )
                for metric in snapshots[0].resources[resource_id]
            },
        )
        for resource_id in expected_resources
    ]
    return system, stages, resources


def build_convergence(
    snapshots: list[MetricSnapshot], requested_run_count: int
) -> list[ConvergenceCheckpoint]:
    tracked = [
        "slaAttainment",
        "averageCycleTime",
        "p95CycleTime",
        "timeWeightedWip",
        "timeWeightedQueueLength",
    ]
    checkpoints = sorted(
        {
            point
            for point in [10, 25, 50, 100, 250, 500, requested_run_count]
            if point <= requested_run_count
        }
    )
    previous: dict[str, float] = {}
    result: list[ConvergenceCheckpoint] = []
    for checkpoint in checkpoints:
        included = [snapshot for snapshot in snapshots if snapshot.run_index < checkpoint]
        metrics: dict[str, RunningMeanPoint] = {}
        if included:
            for metric in tracked:
                mean = sum(snapshot.system[metric] for snapshot in included) / len(included)
                prior = previous.get(metric)
                change = None if prior is None else mean - prior
                if prior is None or prior == 0:
                    relative = None
                else:
                    relative = (mean - prior) / abs(prior)
                metrics[metric] = RunningMeanPoint(
                    mean=mean,
                    change_from_previous=change,
                    relative_change=relative,
                )
                previous[metric] = mean
        result.append(
            ConvergenceCheckpoint(
                requested_run_count=checkpoint,
                successful_run_count=len(included),
                metrics=metrics,
            )
        )
    return result


def _validate_repeated_result(
    request: RepeatedSimulationRequest,
    result: RepeatedSimulationResult,
    snapshots: list[MetricSnapshot],
) -> int:
    checks = 0

    def require(condition: bool, code: str, message: str) -> None:
        if not condition:
            raise RepeatedSimulationError(code, message, result.failed_runs)

    require(
        result.requested_run_count
        == result.successful_run_count + result.failed_run_count,
        "run_accounting",
        "Requested runs do not reconcile",
    )
    checks += 1
    all_indexes = [snapshot.run_index for snapshot in snapshots] + [
        failure.run_index for failure in result.failed_runs
    ]
    require(len(all_indexes) == len(set(all_indexes)), "run_indexes", "Run indexes repeat")
    checks += 1
    seeds = [entry.seed for entry in result.run_seeds]
    require(len(seeds) == len(set(seeds)), "run_seeds", "Run seeds repeat")
    checks += 1
    require(
        seeds == seed_schedule(request.base_seed, request.run_count),
        "seed_schedule",
        "Seed schedule does not match its identifier",
    )
    checks += 1
    aggregates = list(result.system_metrics.values()) + [
        metric for stage in result.stage_metrics for metric in stage.metrics.values()
    ] + [
        metric
        for resource in result.resource_pool_metrics
        for metric in resource.metrics.values()
    ]
    require(
        all(metric.count == result.successful_run_count for metric in aggregates),
        "aggregate_counts",
        "Aggregate counts differ from successful runs",
    )
    checks += 1
    require(
        all(risk.valid_runs == result.successful_run_count for risk in result.risks),
        "risk_denominator",
        "Risk denominator differs from successful runs",
    )
    checks += 1
    successful_indexes = {snapshot.run_index for snapshot in snapshots}
    require(
        result.representative_run.run_index in successful_indexes,
        "representative_membership",
        "Representative run is not successful",
    )
    checks += 1
    require(
        result.representative_run.rerun_snapshot_matches,
        "representative_match",
        "Representative rerun snapshot differs",
    )
    checks += 1
    require(
        successful_indexes.isdisjoint(failure.run_index for failure in result.failed_runs),
        "failed_exclusion",
        "Failed run contributed to aggregates",
    )
    checks += 1
    checkpoint_indexes = [point.requested_run_count for point in result.convergence]
    require(
        checkpoint_indexes == sorted(set(checkpoint_indexes))
        and all(index <= request.run_count for index in checkpoint_indexes),
        "convergence_checkpoints",
        "Convergence checkpoints are invalid",
    )
    checks += 1
    require(
        all(
            math.isfinite(metric.confidence_interval.lower)
            and math.isfinite(metric.confidence_interval.upper)
            for metric in aggregates
        ),
        "confidence_bounds",
        "Confidence bounds must be finite",
    )
    checks += 1
    require(
        result.execution.ordinary_run_included_event_count == 0
        and result.execution.ordinary_run_retained_event_count == 0,
        "ordinary_run_retention",
        "Ordinary repeated runs retained event evidence",
    )
    checks += 1
    require(
        result.execution.representative_rerun_count <= 1
        and result.execution.maximum_simultaneously_retained_single_run_results <= 1,
        "representative_retention",
        "Representative retention exceeded its coordinator limit",
    )
    checks += 1
    return checks


def run_repeated_simulation(
    request: RepeatedSimulationRequest,
    simulation_runner: SimulationRunner = run_simulation,
) -> RepeatedSimulationResult:
    """Run independent seeds sequentially and retain compact scalar evidence."""
    seeds = seed_schedule(request.base_seed, request.run_count)
    snapshots: list[MetricSnapshot] = []
    failures: list[FailedRunEvidence] = []
    total_events = 0
    for run_index, seed in enumerate(seeds):
        try:
            run_result = simulation_runner(
                request.model,
                seed_override=seed,
                observation=request.observation,
                result_detail=ResultDetailConfig(mode="summary"),
            )
            if (
                run_result.result_detail.mode != "summary"
                or run_result.result_detail.included_event_count != 0
                or len(run_result.events) != 0
            ):
                raise RepeatedSimulationError(
                    "ordinary_run_retention",
                    "Ordinary repeated run retained event evidence",
                )
            snapshot = extract_metric_snapshot(run_index, run_result)
            snapshots.append(snapshot)
            total_events += int(snapshot.system["eventCount"])
            del run_result
        except RepeatedSimulationError:
            raise
        except Exception as error:  # safe per-run classification boundary
            failures.append(classify_run_failure(run_index, seed, error))

    ratio = len(snapshots) / request.run_count
    if ratio < request.minimum_successful_run_ratio:
        raise RepeatedSimulationError(
            "minimum_successful_run_ratio",
            "Repeated simulation successful-run ratio is below the configured minimum",
            failures,
        )

    system, stages, resources = aggregate_snapshot_groups(
        snapshots, request.confidence_level
    )
    risk_values = {
        metric: [snapshot.system[metric] for snapshot in snapshots]
        for metric in [
            "slaAttainment",
            "averageCycleTime",
            "p95CycleTime",
            "timeWeightedQueueLength",
            "terminalFailureRate",
        ]
    }
    risks = evaluate_risks(risk_values, request.thresholds)
    selection = select_representative(
        [
            RepresentativeCandidate(
                snapshot.run_index, snapshot.seed, snapshot.representative_vector
            )
            for snapshot in snapshots
        ]
    )
    representative_config = request.representative_run
    detail = ResultDetailConfig(
        mode=representative_config.detail_mode,
        sampled_item_limit=representative_config.sampled_item_limit,
    )
    try:
        representative_result = simulation_runner(
            request.model,
            seed_override=selection.candidate.seed,
            observation=request.observation,
            result_detail=detail,
        )
    except Exception as error:
        failure = classify_run_failure(
            selection.candidate.run_index, selection.candidate.seed, error
        )
        raise RepeatedSimulationError(
            "representative_rerun_failed", "Representative rerun failed", [*failures, failure]
        ) from error
    representative_snapshot = extract_metric_snapshot(
        selection.candidate.run_index, representative_result
    )
    original_snapshot = next(
        snapshot
        for snapshot in snapshots
        if snapshot.run_index == selection.candidate.run_index
    )
    rerun_matches = representative_snapshot == original_snapshot
    representative = RepresentativeRunResult(
        run_index=selection.candidate.run_index,
        seed=selection.candidate.seed,
        distance=selection.distance,
        median_vector=selection.median_vector,
        metric_vector=selection.candidate.vector,
        rerun_snapshot_matches=rerun_matches,
        detail_mode=detail.mode,
        included_event_count=len(representative_result.events),
        result=representative_result,
    )
    result = RepeatedSimulationResult(
        model_name=request.model.name,
        requested_run_count=request.run_count,
        successful_run_count=len(snapshots),
        failed_run_count=len(failures),
        successful_run_ratio=ratio,
        base_seed=request.base_seed,
        seed_schedule_algorithm=SEED_SCHEDULE_ALGORITHM,
        run_seeds=[
            RunSeed(run_index=index, seed=seed) for index, seed in enumerate(seeds)
        ],
        observation=request.observation,
        confidence_level=request.confidence_level,
        system_metrics=system,
        stage_metrics=stages,
        resource_pool_metrics=resources,
        risks=risks,
        convergence_method="observed_running_mean_stability",
        convergence=build_convergence(snapshots, request.run_count),
        failed_runs=failures,
        representative_run=representative,
        execution=RepeatedExecutionMetadata(
            ordinary_run_count=request.run_count,
            ordinary_run_included_event_count=0,
            ordinary_run_retained_event_count=0,
            representative_rerun_count=1,
            maximum_simultaneously_retained_single_run_results=1,
            total_generated_event_count=total_events
            + representative_result.result_detail.total_event_count,
            returned_event_count=len(representative_result.events),
        ),
        integrity=RepeatedIntegrityStatus(checks_run=0),
    )
    checks = _validate_repeated_result(request, result, snapshots)
    return result.model_copy(
        update={"integrity": RepeatedIntegrityStatus(checks_run=checks)}
    )
