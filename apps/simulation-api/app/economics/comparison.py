from __future__ import annotations

from time import perf_counter

from app.domain.economics import (
    CostSnapshot,
    EconomicComparisonRequest,
    EconomicComparisonResult,
    EconomicExecutionMetadata,
    EconomicGuardrailResult,
    EconomicIntegrityStatus,
    EconomicScenarioResult,
    InterventionCostEvidence,
)
from app.domain.models import OperationalModel, SimulationResult
from app.economics.aggregation import (
    aggregate_cost_snapshots,
    paired_component_deltas,
    paired_cost_delta,
)
from app.economics.evaluator import evaluate_cost_snapshot
from app.economics.integrity import validate_economic_integrity
from app.economics.tradeoffs import (
    classify_tradeoff,
    factual_statement,
    incremental_cost_per_improvement,
)
from app.scenarios.coordinator import run_scenario_comparison
from app.scenarios.metrics import METRIC_REGISTRY


def _recurring(snapshot: CostSnapshot) -> float:
    if snapshot.recurring_operating_cost is None:
        raise ValueError("configured economic total is unavailable")
    return snapshot.recurring_operating_cost


def _intervention(
    request: EconomicComparisonRequest,
    scenario_id: str,
    recurring_mean: float | None,
) -> InterventionCostEvidence:
    configured = next(
        (item for item in request.interventions if item.scenario_id == scenario_id), None
    )
    if configured is None:
        return InterventionCostEvidence()
    amortized = (
        configured.one_time_cost / configured.amortization_periods
        if configured.amortization_periods is not None
        else None
    )
    return InterventionCostEvidence(
        one_time_cost=configured.one_time_cost,
        amortization_periods=configured.amortization_periods,
        amortized_cost_per_period=amortized,
        combined_per_period_cost=(
            recurring_mean + amortized
            if recurring_mean is not None and amortized is not None
            else None
        ),
    )


def _guardrails(
    request: EconomicComparisonRequest,
    recurring: float | None,
    per_completion: float | None,
    increase: float | None,
    amortized: float | None,
) -> list[EconomicGuardrailResult]:
    values = [
        (
            "recurringOperatingCost",
            request.economic_guardrails.maximum_recurring_operating_cost,
            recurring,
        ),
        (
            "costPerCompletedItem",
            request.economic_guardrails.maximum_cost_per_completed_item,
            per_completion,
        ),
        (
            "recurringCostIncrease",
            request.economic_guardrails.maximum_recurring_cost_increase,
            increase,
        ),
        (
            "amortizedInterventionCostPerPeriod",
            request.economic_guardrails.maximum_amortized_intervention_cost_per_period,
            amortized,
        ),
    ]
    return [
        EconomicGuardrailResult(
            metric=metric,
            threshold=threshold,
            observed_value=observed,
            passed=observed <= threshold if observed is not None else None,
        )
        for metric, threshold, observed in values
        if threshold is not None
    ]


def run_economic_comparison(
    request: EconomicComparisonRequest,
    *,
    record_evaluation_timing: bool = False,
) -> EconomicComparisonResult:
    snapshots: dict[str, dict[int, CostSnapshot]] = {
        "baseline": {},
        **{item.id: {} for item in request.comparison.scenarios},
    }
    evaluation_seconds = 0.0
    evaluation_count = 0

    def observe(
        variant_id: str,
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
                snapshots[variant_id][run_index] = snapshot
                evaluation_count += 1
        except Exception:
            # Operational execution remains valid; economic evidence is isolated.
            pass
        finally:
            evaluation_seconds += perf_counter() - started

    operational = run_scenario_comparison(request.comparison, run_observer=observe)
    baseline_snapshots = snapshots["baseline"]
    if len(baseline_snapshots) != request.comparison.execution.run_count:
        raise ValueError("baseline economic evaluation failed")
    baseline = aggregate_cost_snapshots(
        list(baseline_snapshots.values()),
        request.comparison.execution.confidence_level,
    )
    results: list[EconomicScenarioResult] = []
    operational_by_id = {item.scenario_id: item for item in operational.scenarios}
    direction = METRIC_REGISTRY[request.comparison.objective.metric].direction
    for definition in request.comparison.scenarios:
        current = snapshots[definition.id]
        paired_indexes = sorted(set(baseline_snapshots) & set(current))
        paired_ratio = len(paired_indexes) / request.comparison.execution.run_count
        op = operational_by_id[definition.id]
        scenario_cost = (
            aggregate_cost_snapshots(
                list(current.values()),
                request.comparison.execution.confidence_level,
            )
            if current
            else None
        )
        delta = None
        lower = higher = tied = None
        component_deltas = {}
        if paired_indexes:
            delta, lower, higher, tied = paired_cost_delta(
                {index: _recurring(baseline_snapshots[index]) for index in paired_indexes},
                {index: _recurring(current[index]) for index in paired_indexes},
                request.comparison.execution.confidence_level,
            )
            component_deltas = paired_component_deltas(
                baseline_snapshots,
                current,
                request.comparison.execution.confidence_level,
            )
        objective = op.paired_metrics.get(request.comparison.objective.metric)
        objective_delta = objective.absolute_delta.mean if objective is not None else None
        probability_improved = (
            objective.improvement.probability_of_improvement if objective is not None else None
        )
        cost_delta = delta.absolute_delta.mean if delta is not None else None
        classification = classify_tradeoff(cost_delta, objective_delta, direction)
        intervention = _intervention(
            request,
            definition.id,
            scenario_cost.recurring_operating_cost.mean if scenario_cost else None,
        )
        guardrails = _guardrails(
            request,
            scenario_cost.recurring_operating_cost.mean if scenario_cost else None,
            scenario_cost.cost_per_completed_item.mean
            if scenario_cost and scenario_cost.cost_per_completed_item
            else None,
            cost_delta,
            intervention.amortized_cost_per_period,
        )
        valid = (
            op.status == "valid"
            and scenario_cost is not None
            and delta is not None
            and paired_ratio >= request.comparison.execution.minimum_paired_run_ratio
        )
        operational_eligible = op.eligible
        economic_eligible = all(item.passed is True for item in guardrails)
        results.append(
            EconomicScenarioResult(
                scenario_id=definition.id,
                scenario_name=definition.name,
                status="valid" if valid else "economic_failed",
                failure_category=None if valid else "economic_pairing_failure",
                baseline_cost=baseline,
                scenario_cost=scenario_cost,
                recurring_cost_delta=delta,
                component_cost_deltas=component_deltas,
                paired_run_count=len(paired_indexes),
                paired_run_ratio=paired_ratio,
                probability_lower_cost=lower,
                probability_higher_cost=higher,
                probability_tied_cost=tied,
                objective_metric=request.comparison.objective.metric,
                objective_mean_paired_delta=objective_delta,
                probability_operationally_improved=probability_improved,
                tradeoff_classification=classification,
                evidence_statement=factual_statement(
                    classification,
                    METRIC_REGISTRY[request.comparison.objective.metric].label.lower(),
                ),
                intervention=intervention,
                economic_guardrails=guardrails,
                combined_eligibility=(
                    operational_eligible and economic_eligible
                    if request.combine_operational_and_economic_eligibility
                    else None
                ),
                incremental_cost_per_observed_improvement=(
                    incremental_cost_per_improvement(cost_delta, objective_delta, direction)
                ),
            )
        )
    provisional = EconomicComparisonResult(
        currency=request.assumptions.currency,
        model_time_unit=request.assumptions.model_time_unit,
        operational_comparison=operational,
        baseline_cost=baseline,
        scenarios=results,
        work_budget=operational.work_budget,
        execution=EconomicExecutionMetadata(
            economic_snapshot_evaluations=evaluation_count,
            economic_evaluation_seconds=(evaluation_seconds if record_evaluation_timing else 0),
        ),
        integrity=EconomicIntegrityStatus(checks_run=22),
    )
    checks = validate_economic_integrity(request, provisional)
    return provisional.model_copy(update={"integrity": EconomicIntegrityStatus(checks_run=checks)})
