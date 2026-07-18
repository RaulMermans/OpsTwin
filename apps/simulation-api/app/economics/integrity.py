from __future__ import annotations

from app.domain.economics import EconomicComparisonRequest, EconomicComparisonResult


def _probabilities_reconcile(lower: float | None, higher: float | None, tied: float | None) -> bool:
    if lower is None:
        return True
    if higher is None or tied is None:
        return False
    return abs(lower + higher + tied - 1) <= 1e-9


def validate_economic_integrity(
    request: EconomicComparisonRequest, result: EconomicComparisonResult
) -> int:
    checks = [
        result.schema_version == "0.7.0",
        result.currency == request.assumptions.currency,
        result.model_time_unit == request.assumptions.model_time_unit,
        result.work_budget == result.operational_comparison.work_budget,
        result.execution.ordinary_run_included_event_count == 0,
        result.execution.ordinary_run_retained_event_count == 0,
        result.execution.economic_snapshot_evaluations
        <= result.operational_comparison.execution.ordinary_simulation_executions,
        result.baseline_cost.recurring_operating_cost.count
        == request.comparison.execution.run_count,
        len(result.scenarios) == len(request.comparison.scenarios),
        [item.scenario_id for item in result.scenarios]
        == [item.id for item in request.comparison.scenarios],
        all(
            item.paired_run_count <= request.comparison.execution.run_count
            for item in result.scenarios
        ),
        all(0 <= item.paired_run_ratio <= 1 for item in result.scenarios),
        all(
            item.intervention.one_time_cost is None or item.intervention.one_time_cost >= 0
            for item in result.scenarios
        ),
        all(
            item.intervention.amortization_periods is not None
            or item.intervention.amortized_cost_per_period is None
            for item in result.scenarios
        ),
        all(
            item.intervention.amortization_periods is not None
            or item.intervention.combined_per_period_cost is None
            for item in result.scenarios
        ),
        all(
            item.recurring_cost_delta is None
            or item.recurring_cost_delta.relative_delta_undefined_count <= item.paired_run_count
            for item in result.scenarios
        ),
        all(
            item.probability_lower_cost is None or item.probability_higher_cost is not None
            for item in result.scenarios
        ),
        all(
            item.probability_lower_cost is None or item.probability_tied_cost is not None
            for item in result.scenarios
        ),
        all(
            _probabilities_reconcile(
                item.probability_lower_cost,
                item.probability_higher_cost,
                item.probability_tied_cost,
            )
            for item in result.scenarios
        ),
        all(item.evidence_statement != "" for item in result.scenarios),
        all(
            item.incremental_cost_label.startswith("Incremental recurring cost")
            for item in result.scenarios
        ),
        all(item.status != "valid" or item.scenario_cost is not None for item in result.scenarios),
        all(
            item.status != "valid" or item.recurring_cost_delta is not None
            for item in result.scenarios
        ),
        all(item.baseline_cost == result.baseline_cost for item in result.scenarios),
        all(
            0 <= failure.run_index < request.comparison.execution.run_count
            for failure in result.execution.observer_failures
        ),
        all(
            failure.variant_id in {"baseline", *(item.id for item in request.comparison.scenarios)}
            for failure in result.execution.observer_failures
        ),
    ]
    if not all(checks):
        raise ValueError("economic integrity validation failed")
    return len(checks)
