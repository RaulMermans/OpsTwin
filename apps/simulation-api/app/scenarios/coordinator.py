from __future__ import annotations

from collections.abc import Callable
from typing import Literal, cast

from app.domain.comparison import (
    AppliedOverrideSummary,
    ComparativeRankingEntry,
    ComparisonExecutionMetadata,
    ComparisonIntegrityStatus,
    ComparisonRepresentatives,
    FactualPairedMetricResult,
    GuardrailEvaluation,
    ImprovementResult,
    PairedMetricResult,
    RepresentativeVariantResult,
    RiskComparisonResult,
    ScenarioComparisonEntry,
    ScenarioComparisonRequest,
    ScenarioComparisonResult,
    ScenarioFailureCategory,
    ScenarioFailureEvidence,
    VariantAggregateResult,
    WorkBudgetResult,
)
from app.domain.models import OperationalModel, ResultDetailConfig, SimulationResult
from app.domain.repeated import (
    FailedRunEvidence,
    RepresentativeRunResult,
    RunSeed,
)
from app.engine.aggregation import (
    RepresentativeCandidate,
    evaluate_risks,
    select_representative,
)
from app.engine.repeated import aggregate_snapshot_groups, build_convergence
from app.engine.seed_schedule import SEED_SCHEDULE_ALGORITHM, seed_schedule
from app.engine.simulator import run_simulation
from app.engine.snapshots import MetricSnapshot, extract_metric_snapshot
from app.scenarios.integrity import (
    ComparisonIntegrityError,
    validate_comparison_integrity,
)
from app.scenarios.materializer import (
    MaterializedScenario,
    ScenarioMaterializationError,
    canonical_model_hash,
    materialize_scenario,
)
from app.scenarios.metrics import (
    METRIC_REGISTRY,
    compare_paired_metric,
    compare_threshold_risk,
)
from app.scenarios.ranking import (
    RankingCandidate,
    evaluate_guardrails,
    rank_candidates,
)

MAX_COMPARISON_WORK_UNITS = 100_000
SimulationRunner = Callable[..., SimulationResult]
ComparisonRunObserver = Callable[[str, OperationalModel, int, SimulationResult], None]


class ScenarioComparisonError(RuntimeError):
    """Safe request-level comparison failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ComparisonWorkBudgetError(ScenarioComparisonError):
    def __init__(self, estimated_work_units: int, maximum_work_units: int) -> None:
        super().__init__(
            "comparison_work_budget_exceeded",
            "Scenario comparison exceeds the synchronous work budget",
        )
        self.estimated_work_units = estimated_work_units
        self.maximum_work_units = maximum_work_units


def _safe_scenario_failure(
    category: ScenarioFailureCategory,
) -> ScenarioFailureEvidence:
    messages = {
        "override_validation": "Scenario override validation failed",
        "materialization_validation": "Scenario materialization validation failed",
        "domain_validation": "Scenario domain validation failed",
        "paired_execution": "Scenario execution did not meet its success policy",
        "paired_ratio_failure": "Scenario paired-run ratio is below the configured minimum",
        "serialization_failure": "Scenario result serialization failed",
    }
    return ScenarioFailureEvidence(category=category, message=messages[category])


def _require_summary_result(result: SimulationResult) -> None:
    if (
        result.result_detail.mode != "summary"
        or result.result_detail.included_event_count != 0
        or result.events
    ):
        raise ScenarioComparisonError(
            "ordinary_run_retention",
            "Ordinary comparison run retained event evidence",
        )


def _risk_values(snapshots: list[MetricSnapshot]) -> dict[str, list[float]]:
    return {
        metric: [snapshot.system[metric] for snapshot in snapshots]
        for metric in (
            "slaAttainment",
            "averageCycleTime",
            "p95CycleTime",
            "timeWeightedQueueLength",
            "terminalFailureRate",
        )
    }


def _variant_result(
    variant_id: str,
    model_hash: str,
    snapshots: list[MetricSnapshot],
    failures: list[FailedRunEvidence],
    request: ScenarioComparisonRequest,
) -> VariantAggregateResult:
    system, stages, resources = aggregate_snapshot_groups(
        snapshots, request.execution.confidence_level
    )
    return VariantAggregateResult(
        variant_id=variant_id,
        model_hash=model_hash,
        successful_run_count=len(snapshots),
        failed_run_count=len(failures),
        successful_run_ratio=len(snapshots) / request.execution.run_count,
        system_metrics=system,
        stage_metrics=stages,
        resource_pool_metrics=resources,
        risks=evaluate_risks(_risk_values(snapshots), request.execution.thresholds),
        convergence=build_convergence(snapshots, request.execution.run_count),
        failed_runs=failures,
    )


def _risk_configurations(
    request: ScenarioComparisonRequest,
) -> list[tuple[str, str, float]]:
    thresholds = request.execution.thresholds
    values = [
        ("slaAttainment", "below", thresholds.minimum_sla_attainment),
        ("averageCycleTime", "above", thresholds.maximum_average_cycle_time),
        ("p95CycleTime", "above", thresholds.maximum_p95_cycle_time),
        (
            "timeWeightedQueueLength",
            "above",
            thresholds.maximum_time_weighted_queue_length,
        ),
        (
            "terminalFailureRate",
            "above",
            thresholds.maximum_terminal_failure_rate,
        ),
    ]
    return [
        (metric, operator, threshold)
        for metric, operator, threshold in values
        if threshold is not None
    ]


def _representative(
    variant_id: str,
    model: object,
    snapshots: dict[int, MetricSnapshot],
    request: ScenarioComparisonRequest,
    simulation_runner: SimulationRunner,
) -> tuple[RepresentativeVariantResult, int, int]:
    selection = select_representative(
        [
            RepresentativeCandidate(
                snapshot.run_index, snapshot.seed, snapshot.representative_vector
            )
            for snapshot in snapshots.values()
        ]
    )
    config = request.representative_evidence
    detail = ResultDetailConfig(
        mode=config.detail_mode,
        sampled_item_limit=config.sampled_item_limit,
    )
    result = simulation_runner(
        model,
        seed_override=selection.candidate.seed,
        observation=request.execution.observation,
        result_detail=detail,
    )
    rerun_snapshot = extract_metric_snapshot(selection.candidate.run_index, result)
    matches = rerun_snapshot == snapshots[selection.candidate.run_index]
    representative = RepresentativeVariantResult(
        variant_id=variant_id,
        representative=RepresentativeRunResult(
            run_index=selection.candidate.run_index,
            seed=selection.candidate.seed,
            distance=selection.distance,
            median_vector=selection.median_vector,
            metric_vector=selection.candidate.vector,
            rerun_snapshot_matches=matches,
            detail_mode=detail.mode,
            included_event_count=len(result.events),
            result=result,
        ),
    )
    return representative, result.result_detail.total_event_count, len(result.events)


def _empty_scenario_entry(
    request: ScenarioComparisonRequest,
    scenario_id: str,
    scenario_name: str,
    baseline_hash: str,
    failure: ScenarioFailureEvidence,
) -> ScenarioComparisonEntry:
    return ScenarioComparisonEntry(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        status="failed",
        failure=failure,
        baseline_model_hash=baseline_hash,
        applied_override_count=0,
        applied_overrides=[],
        requested_run_count=request.execution.run_count,
        baseline_successful_run_count=request.execution.run_count,
        scenario_successful_run_count=0,
        paired_run_count=0,
        paired_run_ratio=0,
        paired_run_indexes=[],
        baseline_only_successful_indexes=list(range(request.execution.run_count)),
        scenario_only_successful_indexes=[],
        failed_indexes=list(range(request.execution.run_count)),
        paired_metrics={},
        resource_utilization_deltas={},
        risk_comparisons=[],
        guardrails=[],
        eligible=False,
        evidence_statements=[],
    )


def run_scenario_comparison(
    request: ScenarioComparisonRequest,
    simulation_runner: SimulationRunner = run_simulation,
    *,
    run_observer: ComparisonRunObserver | None = None,
) -> ScenarioComparisonResult:
    baseline_items = sum(source.item_count for source in request.baseline_model.sources)
    variants = 1 + len(request.scenarios)
    work_units = baseline_items * request.execution.run_count * variants
    if work_units > MAX_COMPARISON_WORK_UNITS:
        raise ComparisonWorkBudgetError(work_units, MAX_COMPARISON_WORK_UNITS)
    work_budget = WorkBudgetResult(
        baseline_item_count=baseline_items,
        model_variants=variants,
        run_count=request.execution.run_count,
        estimated_total_item_executions=work_units,
        estimated_work_units=work_units,
        maximum_work_units=MAX_COMPARISON_WORK_UNITS,
    )
    baseline_hash = canonical_model_hash(request.baseline_model)
    materialized: dict[str, MaterializedScenario] = {}
    scenario_entries: dict[str, ScenarioComparisonEntry] = {}
    for definition in request.scenarios:
        try:
            materialized[definition.id] = materialize_scenario(
                request.baseline_model, definition
            )
        except ScenarioMaterializationError as error:
            category = cast(ScenarioFailureCategory, error.category)
            scenario_entries[definition.id] = _empty_scenario_entry(
                request,
                definition.id,
                definition.name,
                baseline_hash,
                _safe_scenario_failure(category),
            )

    seeds = seed_schedule(request.execution.base_seed, request.execution.run_count)
    baseline_snapshots: dict[int, MetricSnapshot] = {}
    scenario_snapshots: dict[str, dict[int, MetricSnapshot]] = {
        scenario_id: {} for scenario_id in materialized
    }
    scenario_failures: dict[str, list[FailedRunEvidence]] = {
        scenario_id: [] for scenario_id in materialized
    }
    total_events = 0
    ordinary_executions = 0
    for run_index, seed in enumerate(seeds):
        try:
            baseline_result = simulation_runner(
                request.baseline_model,
                seed_override=seed,
                observation=request.execution.observation,
                result_detail=ResultDetailConfig(mode="summary"),
            )
            ordinary_executions += 1
            _require_summary_result(baseline_result)
            baseline_snapshot = extract_metric_snapshot(run_index, baseline_result)
            if run_observer is not None:
                run_observer("baseline", request.baseline_model, run_index, baseline_result)
            baseline_snapshots[run_index] = baseline_snapshot
            total_events += int(baseline_snapshot.system["eventCount"])
            del baseline_result
        except Exception as error:
            raise ScenarioComparisonError(
                "baseline_execution_failed", "Baseline comparison execution failed"
            ) from error
        for scenario_id, scenario in materialized.items():
            try:
                scenario_result = simulation_runner(
                    scenario.model,
                    seed_override=seed,
                    observation=request.execution.observation,
                    result_detail=ResultDetailConfig(mode="summary"),
                )
                ordinary_executions += 1
                _require_summary_result(scenario_result)
                snapshot = extract_metric_snapshot(run_index, scenario_result)
                if run_observer is not None:
                    run_observer(scenario_id, scenario.model, run_index, scenario_result)
                scenario_snapshots[scenario_id][run_index] = snapshot
                total_events += int(snapshot.system["eventCount"])
                del scenario_result
            except ScenarioComparisonError:
                raise
            except Exception:
                scenario_failures[scenario_id].append(
                    FailedRunEvidence(
                        run_index=run_index,
                        seed=seed,
                        category="execution_failure",
                        message="Scenario simulation execution failed",
                    )
                )

    baseline_variant = _variant_result(
        "baseline",
        baseline_hash,
        list(baseline_snapshots.values()),
        [],
        request,
    )
    ranking_candidates: list[RankingCandidate] = []
    for definition in request.scenarios:
        if definition.id not in materialized:
            continue
        scenario = materialized[definition.id]
        snapshots = scenario_snapshots[definition.id]
        failures = scenario_failures[definition.id]
        if not snapshots:
            scenario_entries[definition.id] = ScenarioComparisonEntry(
                scenario_id=definition.id,
                scenario_name=definition.name,
                status="failed",
                failure=_safe_scenario_failure("paired_execution"),
                baseline_model_hash=scenario.baseline_model_hash,
                scenario_model_hash=scenario.scenario_model_hash,
                applied_override_count=scenario.applied_override_count,
                applied_overrides=[
                    AppliedOverrideSummary.model_validate(item)
                    for item in scenario.applied_overrides
                ],
                requested_run_count=request.execution.run_count,
                baseline_successful_run_count=len(baseline_snapshots),
                scenario_successful_run_count=0,
                paired_run_count=0,
                paired_run_ratio=0,
                paired_run_indexes=[],
                baseline_only_successful_indexes=sorted(baseline_snapshots),
                scenario_only_successful_indexes=[],
                failed_indexes=list(range(request.execution.run_count)),
                paired_metrics={},
                resource_utilization_deltas={},
                risk_comparisons=[],
                guardrails=[],
                eligible=False,
                evidence_statements=[],
            )
            continue
        variant = _variant_result(
            definition.id,
            scenario.scenario_model_hash,
            list(snapshots.values()),
            failures,
            request,
        )
        paired_indexes = sorted(set(baseline_snapshots) & set(snapshots))
        paired_ratio = len(paired_indexes) / request.execution.run_count
        successful_ratio = len(snapshots) / request.execution.run_count
        status: Literal["valid", "failed"] = "valid"
        failure: ScenarioFailureEvidence | None = None
        if successful_ratio < request.execution.minimum_successful_run_ratio:
            status = "failed"
            failure = _safe_scenario_failure("paired_execution")
        elif paired_ratio < request.execution.minimum_paired_run_ratio:
            status = "failed"
            failure = _safe_scenario_failure("paired_ratio_failure")
        paired_metrics: dict[str, PairedMetricResult] = {}
        resource_utilization_deltas: dict[str, FactualPairedMetricResult] = {}
        risk_comparisons: list[RiskComparisonResult] = []
        guardrails: list[GuardrailEvaluation] = []
        eligible = False
        statements: list[str] = []
        if status == "valid":
            for metric in METRIC_REGISTRY:
                if (
                    metric == "resourcePoolUtilization"
                    or metric not in baseline_snapshots[0].system
                ):
                    continue
                comparison = compare_paired_metric(
                    {
                        index: baseline_snapshots[index].system[metric]
                        for index in paired_indexes
                    },
                    {
                        index: snapshots[index].system[metric]
                        for index in paired_indexes
                    },
                    metric=metric,
                    confidence_level=request.execution.confidence_level,
                )
                paired_metrics[metric] = PairedMetricResult(
                    metric=metric,
                    absolute_delta=comparison.absolute,
                    relative_delta=comparison.relative,
                    relative_delta_undefined_count=(
                        comparison.relative_delta_undefined_count
                    ),
                    improvement=ImprovementResult(
                        **comparison.improvement.__dict__
                    ),
                )
            first_paired_index = paired_indexes[0]
            common_resource_ids = sorted(
                set(baseline_snapshots[first_paired_index].resources)
                & set(snapshots[first_paired_index].resources)
            )
            for resource_id in common_resource_ids:
                comparison = compare_paired_metric(
                    {
                        index: baseline_snapshots[index].resources[resource_id][
                            "utilization"
                        ]
                        for index in paired_indexes
                    },
                    {
                        index: snapshots[index].resources[resource_id]["utilization"]
                        for index in paired_indexes
                    },
                    metric="resourcePoolUtilization",
                    confidence_level=request.execution.confidence_level,
                )
                resource_utilization_deltas[resource_id] = FactualPairedMetricResult(
                    absolute_delta=comparison.absolute,
                    relative_delta=comparison.relative,
                    relative_delta_undefined_count=(
                        comparison.relative_delta_undefined_count
                    ),
                )
            for metric, operator, threshold in _risk_configurations(request):
                risk_comparison = compare_threshold_risk(
                    {
                        index: baseline_snapshots[index].system[metric]
                        for index in paired_indexes
                    },
                    {
                        index: snapshots[index].system[metric]
                        for index in paired_indexes
                    },
                    metric=metric,
                    operator=cast(Literal["above", "below"], operator),
                    threshold=threshold,
                )
                risk_comparisons.append(
                    RiskComparisonResult(**risk_comparison.__dict__)
                )
            resource_means = {
                resource.resource_pool_id: {
                    metric: aggregate.mean
                    for metric, aggregate in resource.metrics.items()
                }
                for resource in variant.resource_pool_metrics
            }
            evaluated = evaluate_guardrails(
                request.guardrails,
                system_means={
                    metric: aggregate.mean
                    for metric, aggregate in variant.system_metrics.items()
                },
                resource_means=resource_means,
            )
            guardrails = [GuardrailEvaluation(**item.__dict__) for item in evaluated]
            eligible = all(item.passed for item in guardrails)
            objective = paired_metrics[request.objective.metric]
            improvement = objective.improvement
            statements = [
                (
                    f"{request.objective.metric} improved in "
                    f"{improvement.improved_count} of "
                    f"{improvement.valid_paired_run_count} paired runs."
                ),
                (
                    f"{request.objective.metric} mean paired delta was "
                    f"{objective.absolute_delta.mean:.6g}."
                ),
            ]
            ranking_candidates.append(
                RankingCandidate(
                    scenario_id=definition.id,
                    comparison_valid=True,
                    guardrails_passed=eligible,
                    objective_mean_delta=objective.absolute_delta.mean,
                    probability_of_improvement=(
                        objective.improvement.probability_of_improvement
                    ),
                    confidence_interval_width=(
                        objective.absolute_delta.confidence_interval.upper
                        - objective.absolute_delta.confidence_interval.lower
                    ),
                )
            )
        scenario_entries[definition.id] = ScenarioComparisonEntry(
            scenario_id=definition.id,
            scenario_name=definition.name,
            status=status,
            failure=failure,
            baseline_model_hash=scenario.baseline_model_hash,
            scenario_model_hash=scenario.scenario_model_hash,
            applied_override_count=scenario.applied_override_count,
            applied_overrides=[
                AppliedOverrideSummary.model_validate(item) for item in scenario.applied_overrides
            ],
            variant=variant,
            requested_run_count=request.execution.run_count,
            baseline_successful_run_count=len(baseline_snapshots),
            scenario_successful_run_count=len(snapshots),
            paired_run_count=len(paired_indexes),
            paired_run_ratio=paired_ratio,
            paired_run_indexes=paired_indexes,
            baseline_only_successful_indexes=sorted(
                set(baseline_snapshots) - set(snapshots)
            ),
            scenario_only_successful_indexes=sorted(
                set(snapshots) - set(baseline_snapshots)
            ),
            failed_indexes=sorted(
                set(range(request.execution.run_count)) - set(paired_indexes)
            ),
            paired_metrics=paired_metrics,
            resource_utilization_deltas=resource_utilization_deltas,
            risk_comparisons=risk_comparisons,
            guardrails=guardrails,
            eligible=eligible,
            evidence_statements=statements,
        )

    ranked_rows = rank_candidates(
        ranking_candidates, objective_metric=request.objective.metric
    )
    ranking = [
        ComparativeRankingEntry(
            rank=row.rank,
            scenario_id=row.scenario_id,
            guardrails_passed=row.guardrails_passed,
            objective_metric=row.objective_metric,
            objective_mean_delta=row.objective_mean_delta,
            probability_of_improvement=row.probability_of_improvement,
            confidence_interval_width=row.confidence_interval_width,
            tie_break_explanation=row.tie_break_explanation,
        )
        for row in ranked_rows
        if row.rank is not None
    ]
    baseline_representative = scenario_representative = None
    representative_events = returned_events = representative_count = 0
    if request.representative_evidence.baseline:
        baseline_representative, generated, returned = _representative(
            "baseline",
            request.baseline_model,
            baseline_snapshots,
            request,
            simulation_runner,
        )
        representative_count += 1
        representative_events += generated
        returned_events += returned
    if request.representative_evidence.top_ranked_scenario and ranking:
        selected_id = ranking[0].scenario_id
        scenario_representative, generated, returned = _representative(
            selected_id,
            materialized[selected_id].model,
            scenario_snapshots[selected_id],
            request,
            simulation_runner,
        )
        representative_count += 1
        representative_events += generated
        returned_events += returned
    result = ScenarioComparisonResult(
        baseline_model_hash=baseline_hash,
        requested_run_count=request.execution.run_count,
        base_seed=request.execution.base_seed,
        seed_schedule_algorithm=SEED_SCHEDULE_ALGORITHM,
        run_seeds=[
            RunSeed(run_index=index, seed=seed) for index, seed in enumerate(seeds)
        ],
        confidence_level=request.execution.confidence_level,
        work_budget=work_budget,
        baseline=baseline_variant,
        scenarios=[scenario_entries[scenario.id] for scenario in request.scenarios],
        objective=request.objective,
        ranking=ranking,
        representatives=ComparisonRepresentatives(
            baseline=baseline_representative,
            scenario=scenario_representative,
        ),
        execution=ComparisonExecutionMetadata(
            execution_order="run_index_then_baseline_then_scenarios",
            ordinary_simulation_executions=ordinary_executions,
            representative_reruns=representative_count,
            maximum_simultaneously_retained_event_rich_results=representative_count,
            total_generated_event_count=total_events + representative_events,
            returned_event_count=returned_events,
        ),
        integrity=ComparisonIntegrityStatus(checks_run=1),
    )
    try:
        checks = validate_comparison_integrity(
            request, result, baseline_snapshots, scenario_snapshots
        )
    except ComparisonIntegrityError as error:
        raise ScenarioComparisonError(
            "comparison_integrity_failed", "Comparison integrity validation failed"
        ) from error
    return result.model_copy(
        update={"integrity": ComparisonIntegrityStatus(checks_run=checks)}
    )
