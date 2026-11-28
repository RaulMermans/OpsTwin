from __future__ import annotations

from time import perf_counter
from typing import Any, Literal

from pydantic import Field

from app.domain.decision import (
    BreakEvenEvidence,
    BreakEvenExploreRequest,
    BreakEvenPoint,
    DecisionAssumptions,
    DecisionBrief,
    DecisionConstraints,
    DecisionEvaluationResult,
    DecisionState,
    StrategyEconomics,
)
from app.domain.models import ContractModel
from app.interventions.catalog import ExperimentExecution, NamedAlternative
from app.interventions.execute import MultiExperimentEvidence
from app.interventions.identity import (
    economic_assumption_identity,
    economic_evaluation_identity,
    operational_experiment_identity,
)

FINANCIAL_ONLY = {
    "aiSubscriptionMonthly",
    "implementationCost",
    "realizationRate",
    "monthlyStaffCostPerFte",
    "aiCostPerAutomatedCase",
}


class DecisionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DecisionEvaluationRequest(ContractModel):
    contract_version: str = "cg7.v1"
    fixture_id: str | None = None
    alternatives: list[NamedAlternative] = Field(min_length=1, max_length=3)
    execution: ExperimentExecution
    experiment_identity: str = Field(min_length=16, max_length=64)
    evidence: MultiExperimentEvidence | None = None
    evidence_token: str | None = None
    assumptions: DecisionAssumptions
    constraints: DecisionConstraints = Field(default_factory=DecisionConstraints)
    explore: BreakEvenExploreRequest | None = None


def _finite(value: Any) -> float | None:  # noqa: ANN401
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _metric_mean(metrics: dict[str, Any] | None, key: str) -> float | None:
    packed = (metrics or {}).get(key)
    if not isinstance(packed, dict):
        packed = getattr(packed, "mean", None)
        return _finite(packed)
    return _finite(packed.get("mean"))


def _busy_hours(resource_metrics: dict[str, Any] | None) -> float | None:
    if not resource_metrics:
        return None
    total = 0.0
    found = False
    for pool in resource_metrics.values():
        if not isinstance(pool, dict):
            continue
        minutes = _metric_mean(pool, "busyTime")
        if minutes is None:
            continue
        total += minutes
        found = True
    if not found:
        return None
    return total / 60.0


def _automated_cases(kind: str, completions: float | None, alternative: NamedAlternative) -> float:
    if completions is None:
        return 0.0
    intervention = alternative.intervention
    if kind == "hybrid":
        return completions * float(getattr(intervention, "auto_complete_fraction", 0) or 0)
    if kind == "ai_assisted":
        return completions * float(getattr(intervention, "coverage", 0) or 0)
    return 0.0


def _staff_fte(assumptions: DecisionAssumptions, kind: str, alternative: NamedAlternative | None) -> float:  # noqa: E501
    extra_triage = extra_resolution = 0
    if alternative is not None and kind == "capacity":
        extra_triage = int(getattr(alternative.intervention, "extra_triage_capacity", 0) or 0)
        extra_resolution = int(
            getattr(alternative.intervention, "extra_resolution_capacity", 0) or 0
        )
    return (
        assumptions.baseline_triage_fte
        + extra_triage
        + assumptions.baseline_resolution_fte
        + extra_resolution
    )


def _uses_ai(kind: str) -> bool:
    return kind in {"ai_assisted", "hybrid"}


def evaluate_strategy_economics(
    *,
    strategy_id: str,
    kind: str,
    alternative: NamedAlternative | None,
    ops: dict[str, Any],
    baseline_ops: dict[str, Any],
    assumptions: DecisionAssumptions,
    constraints: DecisionConstraints,
) -> StrategyEconomics:
    months = assumptions.evaluation_months
    basis = assumptions.evaluation_basis
    completions = ops.get("completions")
    cycle = ops.get("cycle")
    unsuccessful = ops.get("unsuccessful")
    busy_hours = ops.get("busy_hours")
    baseline_busy = baseline_ops.get("busy_hours")
    baseline_fte = _staff_fte(assumptions, "baseline", None)
    fte = _staff_fte(assumptions, kind, alternative)
    hourly = assumptions.monthly_staff_cost_per_fte / assumptions.paid_hours_per_month
    simulated_released = None
    if busy_hours is not None and baseline_busy is not None:
        simulated_released = baseline_busy - busy_hours
    automated_sim = _automated_cases(kind, completions, alternative) if alternative else 0.0
    notes: list[str] = [
        "Released processing hours are not cash savings unless a realization mechanism is selected.",  # noqa: E501
        "Simulated utilization is not treated as payroll expenditure.",
    ]
    scale = 1.0
    withhold_period = basis == "fixed_workload"
    if basis == "recurring_period":
        demand = assumptions.expected_demand_per_month
        if demand is None or completions is None or completions <= 0:
            withhold_period = True
            notes.append(
                "Period-based ROI and payback are withheld because demand or simulated completions are insufficient."  # noqa: E501
            )
        else:
            scale = (demand * months) / completions
            notes.append(
                f"Recurring-period results apply linear per-case scaling of {scale:.4g} "
                "from the simulated workload. Nonlinear queueing is not extrapolated."
            )
            cycle_base = baseline_ops.get("cycle")
            if (
                cycle is not None
                and cycle_base is not None
                and abs(cycle - cycle_base) > 0.05 * max(abs(cycle_base), 1.0)
            ):
                notes.append(
                    "Cycle time changed with the intervention, so scaled cash results are exploratory per-case projections, not a re-simulated period horizon."  # noqa: E501
                )
    if basis == "fixed_workload":
        staff_cost = None if busy_hours is None else busy_hours * hourly
        incremental_staff = 0.0
        notes.append(
            "Fixed-workload staffing is the loaded cost of simulated busy hours for this demand, not calendar FTE payroll."  # noqa: E501
        )
        if kind == "capacity":
            notes.append(
                "Extra FTE calendar payroll is omitted in fixed-workload mode. Use recurring_period to cost hiring."  # noqa: E501
            )
        ai_usage = assumptions.ai_cost_per_automated_case * automated_sim
        ai_recurring = ai_usage
        notes.append("AI subscription is a period cost and is omitted from fixed-workload totals.")
        implementation = assumptions.implementation_cost if _uses_ai(kind) else 0.0
        released_hours = simulated_released
        potential = None if released_hours is None else max(0.0, released_hours) * hourly
        incremental_ai = ai_usage
        incremental_investment = incremental_staff + ai_usage + implementation
        total_cost = (staff_cost or 0.0) + ai_usage
        recurring = None
    else:
        staff_cost = fte * assumptions.monthly_staff_cost_per_fte * months
        baseline_staff = baseline_fte * assumptions.monthly_staff_cost_per_fte * months
        incremental_staff = staff_cost - baseline_staff
        notes.append("Staffing cost is calendar payroll for modeled FTE over the selected months.")
        automated = automated_sim * scale
        ai_usage = assumptions.ai_cost_per_automated_case * automated
        ai_recurring = (assumptions.ai_subscription_monthly * months + ai_usage) if _uses_ai(kind) else 0.0  # noqa: E501
        implementation = assumptions.implementation_cost if _uses_ai(kind) else 0.0
        released_hours = None if simulated_released is None else simulated_released * scale
        potential = None if released_hours is None else max(0.0, released_hours) * hourly
        incremental_ai = ai_recurring + implementation
        incremental_investment = incremental_staff + incremental_ai
        total_cost = staff_cost + ai_recurring + implementation
        recurring = staff_cost + ai_recurring
    realizable: float | None = 0.0
    if assumptions.realization_mechanism != "none" and potential is not None:
        realizable = potential * assumptions.realization_rate
        notes.append(
            f"Realizable cash uses {assumptions.realization_mechanism} at realization rate "
            f"{assumptions.realization_rate}."
        )
    elif assumptions.realization_mechanism != "none":
        realizable = None
        notes.append("Released hours were unavailable, so realizable cash is unavailable.")
    current_exposure = (
        (assumptions.baseline_triage_fte + assumptions.baseline_resolution_fte)
        * assumptions.paid_hours_per_month
        * months
    )
    financial_unsupported = False
    if basis == "recurring_period" and baseline_busy is not None and not withhold_period:
        period_busy = baseline_busy * scale
        if current_exposure > 0 and period_busy > current_exposure * 1.05:
            notes.append(
                f"Modeled period processing ({period_busy:.1f} h) exceeds staffed paid hours "
                f"({current_exposure:.1f} h). Cash realization is withheld."
            )
            financial_unsupported = True
            realizable = None
    if (
        not financial_unsupported
        and released_hours is not None
        and current_exposure > 0
        and released_hours > current_exposure + 1e-6
    ):
        notes.append(
            f"Released hours ({released_hours:.1f}) exceed staffed paid hours "
            f"({current_exposure:.1f} h) in the evaluation period."
        )
        payroll_like = assumptions.realization_mechanism in {
            "realizable_payroll_reduction",
            "reduced_overtime",
        }
        if payroll_like:
            notes.append(
                "Payroll or overtime cash is withheld because it cannot exceed paid working hours."
            )
            financial_unsupported = True
            realizable = None
        elif assumptions.realization_mechanism in {"avoided_hiring", "reduced_outsourcing"}:
            notes.append(
                "This cash result depends on avoided future expenditure, not a reduction of current payroll."  # noqa: E501
            )
    if financial_unsupported:
        notes.append("Financial recommendation is withheld. Operational results remain available.")
    net = None
    roi = None
    if realizable is not None:
        net = realizable - incremental_investment
        if incremental_investment > 0 and not withhold_period:
            roi = net / incremental_investment
        elif withhold_period:
            notes.append("Period-based ROI is withheld on a fixed-workload measurement basis.")
    payback_months = None
    payback_status: Literal["recovered_within_horizon", "no_payback", "not_applicable"] = (
        "not_applicable" if withhold_period else "no_payback"
    )
    monthly_net = None
    if realizable is not None and not withhold_period:
        monthly_net = (realizable - (incremental_staff + (ai_recurring if basis == "recurring_period" else 0.0))) / months  # noqa: E501
    if withhold_period:
        payback_status = "not_applicable"
        notes.append("Payback is withheld unless a recurring-period demand projection is used.")
    elif implementation <= 0:
        if monthly_net is not None and monthly_net >= 0 and incremental_investment <= 0:
            payback_months = 0.0
            payback_status = "recovered_within_horizon"
        elif monthly_net is not None and monthly_net > 0:
            payback_months = 0.0
            payback_status = "recovered_within_horizon"
        else:
            payback_status = (
                "not_applicable"
                if implementation == 0 and incremental_investment <= 0
                else "no_payback"
            )
    elif monthly_net is None or monthly_net <= 0:
        payback_status = "no_payback"
    else:
        payback_months = implementation / monthly_net
        payback_status = "recovered_within_horizon" if payback_months <= months else "no_payback"
    cost_per = None
    if completions is not None and completions > 0:
        if basis == "fixed_workload":
            cost_per = total_cost / completions
        elif scale > 0:
            cost_per = total_cost / (completions * scale)
    potential_value = potential if assumptions.value_released_capacity else None
    if potential_value is not None:
        notes.append(
            "Potential capacity value is theoretical productivity, not counted in net benefit or ROI."  # noqa: E501
        )
    cycle_base = baseline_ops.get("cycle")
    improved_ops = cycle is not None and cycle_base is not None and cycle < cycle_base - 1e-9
    released = released_hours is not None and released_hours > 1e-9
    state = _classify(
        net=None if withhold_period else net,
        improved_ops=improved_ops,
        released=released,
        realizable=0.0 if realizable is None else realizable,
        kind=kind,
        constraints=constraints,
        cycle=cycle,
        completions=completions,
        implementation=implementation,
        ai_recurring=ai_recurring,
        incremental_staff=incremental_staff,
        payback_months=payback_months,
        payback_status=payback_status,
        evaluation_months=months,
        withhold_period=withhold_period,
        financial_unsupported=financial_unsupported,
    )
    return StrategyEconomics(
        strategy_id=strategy_id,
        intervention_kind=kind,
        status="valid",
        measurement_mode=basis,
        comparable_completions=True,
        average_cycle_time=cycle,
        successful_completions=completions,
        unsuccessful_outcomes=unsuccessful,
        existing_operating_expenditure=staff_cost,
        incremental_staffing_cost=incremental_staff,
        incremental_ai_cost=incremental_ai,
        one_time_implementation_expenditure=implementation,
        recurring_operating_expenditure=recurring,
        total_modeled_cost=total_cost,
        cost_per_successful_completion=cost_per,
        released_human_hours=released_hours,
        realizable_cash_benefit=realizable,
        potential_capacity_value=potential_value,
        incremental_investment=incremental_investment,
        net_benefit=net,
        roi=roi,
        payback_months=payback_months if payback_status == "recovered_within_horizon" else None,
        payback_status=payback_status,
        decision_state=state,
        notes=notes,
    )


def _classify(
    *,
    net: float | None,
    improved_ops: bool,
    released: bool,
    realizable: float,
    kind: str,
    constraints: DecisionConstraints,
    cycle: float | None,
    completions: float | None,
    implementation: float,
    ai_recurring: float,
    incremental_staff: float,
    payback_months: float | None,
    payback_status: str,
    evaluation_months: int = 12,
    withhold_period: bool = False,
    financial_unsupported: bool = False,
) -> DecisionState:
    months = evaluation_months
    if constraints.maximum_cycle_time is not None and cycle is not None:
        if cycle > constraints.maximum_cycle_time:
            return "not_justified_under_the_selected_assumptions"
    if constraints.minimum_completions is not None and completions is not None:
        if completions < constraints.minimum_completions:
            return "not_justified_under_the_selected_assumptions"
    if constraints.maximum_implementation_cost is not None:
        if implementation > constraints.maximum_implementation_cost:
            return "not_justified_under_the_selected_assumptions"
    monthly_recurring = (ai_recurring + max(0.0, incremental_staff)) / max(months, 1)
    if constraints.maximum_recurring_monthly is not None:
        if monthly_recurring > constraints.maximum_recurring_monthly:
            return "not_justified_under_the_selected_assumptions"
    if (
        constraints.maximum_payback_months is not None
        and payback_status != "recovered_within_horizon"
    ):
        return "not_justified_under_the_selected_assumptions"
    if (
        constraints.maximum_payback_months is not None
        and payback_months is not None
        and payback_months > constraints.maximum_payback_months
    ):
        return "not_justified_under_the_selected_assumptions"
    if withhold_period:
        if improved_ops:
            return "suitable_for_controlled_pilot_evaluation"
        if released:
            return "capacity_releasing_without_cash_savings"
        return "insufficient_evidence_for_a_decision"
    if financial_unsupported:
        if improved_ops:
            return "operationally_beneficial_financially_unattractive"
        if released:
            return "capacity_releasing_without_cash_savings"
        return "insufficient_evidence_for_a_decision"
    if net is not None and net > 0:
        return "economically_attractive_under_current_assumptions"
    if improved_ops and (net is None or net <= 0):
        if implementation > 0 and implementation <= 15_000:
            return "suitable_for_controlled_pilot_evaluation"
        return "operationally_beneficial_financially_unattractive"
    if released and realizable <= 0:
        return "capacity_releasing_without_cash_savings"
    if kind == "capacity" and not improved_ops and (net is None or net < 0):
        return "not_justified_under_the_selected_assumptions"
    if net is not None and net <= 0:
        return "not_justified_under_the_selected_assumptions"
    return "insufficient_evidence_for_a_decision"


def _ops_from_metrics(metrics: dict[str, Any], resources: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "cycle": _metric_mean(metrics, "averageCycleTime"),
        "completions": _metric_mean(metrics, "completedItems"),
        "unsuccessful": _metric_mean(metrics, "terminallyFailedItems"),
        "throughput": _metric_mean(metrics, "completionRate"),
        "busy_hours": _busy_hours(resources),
    }


def _patch_assumptions(assumptions: DecisionAssumptions, parameter: str, value: float) -> DecisionAssumptions:  # noqa: E501
    data = assumptions.model_dump()
    mapping = {
        "aiSubscriptionMonthly": "ai_subscription_monthly",
        "implementationCost": "implementation_cost",
        "realizationRate": "realization_rate",
        "monthlyStaffCostPerFte": "monthly_staff_cost_per_fte",
        "aiCostPerAutomatedCase": "ai_cost_per_automated_case",
    }
    data[mapping[parameter]] = value
    return DecisionAssumptions.model_validate(data)


def _current_parameter(assumptions: DecisionAssumptions, parameter: str) -> float:
    mapping = {
        "aiSubscriptionMonthly": assumptions.ai_subscription_monthly,
        "implementationCost": assumptions.implementation_cost,
        "realizationRate": assumptions.realization_rate,
        "monthlyStaffCostPerFte": assumptions.monthly_staff_cost_per_fte,
        "aiCostPerAutomatedCase": assumptions.ai_cost_per_automated_case,
    }
    return float(mapping[parameter])


def _threshold(
    points: list[BreakEvenPoint],
) -> tuple[
    float | None, Literal["one_threshold", "no_break_even_in_range", "insufficient_evidence"]
]:
    if len(points) < 2 or any(point.net_benefit is None for point in points):
        return None, "insufficient_evidence"
    first = points[0].net_benefit
    assert first is not None
    sign0 = first >= 0
    crossings: list[float] = []
    for left, right in zip(points, points[1:], strict=False):
        assert left.net_benefit is not None and right.net_benefit is not None
        if (left.net_benefit >= 0) != (right.net_benefit >= 0):
            span = right.parameter_value - left.parameter_value
            if span == 0:
                continue
            ratio = abs(left.net_benefit) / (abs(left.net_benefit) + abs(right.net_benefit))
            crossings.append(left.parameter_value + ratio * span)
    if not crossings:
        return None, "no_break_even_in_range"
    if sign0 is False and points[-1].net_benefit is not None and points[-1].net_benefit >= 0:
        return crossings[0], "one_threshold"
    if sign0 is True and points[-1].net_benefit is not None and points[-1].net_benefit < 0:
        return crossings[0], "one_threshold"
    return crossings[0], "one_threshold"


def _mark_dominated(rows: list[StrategyEconomics]) -> list[StrategyEconomics]:
    valid = [row for row in rows if row.status == "valid" and row.strategy_id != "baseline"]
    updated: list[StrategyEconomics] = []
    for row in rows:
        if row.strategy_id == "baseline" or row.status != "valid":
            updated.append(row)
            continue
        dominated = False
        for other in valid:
            if other.strategy_id == row.strategy_id:
                continue
            better_cost = (
                other.net_benefit is not None
                and row.net_benefit is not None
                and other.net_benefit >= row.net_benefit + 1e-9
            )
            better_cycle = (
                other.average_cycle_time is not None
                and row.average_cycle_time is not None
                and other.average_cycle_time <= row.average_cycle_time - 1e-9
            )
            not_worse_cost = (
                other.net_benefit is not None
                and row.net_benefit is not None
                and other.net_benefit >= row.net_benefit - 1e-9
            )
            not_worse_cycle = (
                other.average_cycle_time is not None
                and row.average_cycle_time is not None
                and other.average_cycle_time <= row.average_cycle_time + 1e-9
            )
            if (better_cost and not_worse_cycle) or (better_cycle and not_worse_cost):
                if better_cost or better_cycle:
                    dominated = True
                    break
        if dominated and row.decision_state not in {
            "insufficient_evidence_for_a_decision",
            "not_justified_under_the_selected_assumptions",
        }:
            updated.append(row.model_copy(update={"decision_state": "dominated_by_another_modeled_strategy"}))  # noqa: E501
        else:
            updated.append(row)
    return updated


def _brief(
    evidence: MultiExperimentEvidence,
    rows: list[StrategyEconomics],
    assumptions: DecisionAssumptions,
    break_even: BreakEvenEvidence | None,
) -> DecisionBrief:
    operational = []
    economic = []
    for row in rows:
        if row.strategy_id == "baseline":
            continue
        if row.average_cycle_time is not None:
            operational.append(
                f"{row.strategy_id}: modeled mean cycle time {row.average_cycle_time:.3f} minutes "
                f"on a fixed workload of {row.successful_completions} completions."
            )
        if row.released_human_hours is not None:
            operational.append(
                f"{row.strategy_id}: released human processing {row.released_human_hours:.3f} hours "  # noqa: E501
                "in the simulated workload (not jobs eliminated)."
            )
        if row.net_benefit is not None:
            economic.append(
                f"{row.strategy_id}: net benefit {row.net_benefit:.2f} {assumptions.currency} "
                f"({row.decision_state.replace('_', ' ')})."
            )
        if row.roi is None and row.incremental_investment == 0:
            economic.append(f"{row.strategy_id}: ROI unavailable because incremental investment is zero.")  # noqa: E501
    risks = [
        "Economic results are conditional on summarized operational means, not ROI confidence intervals.",  # noqa: E501
        "Throughput and utilization use scenario-specific until-empty durations and are not used as cash denominators.",  # noqa: E501
    ]
    if evidence.synthetic:
        risks.insert(0, "Synthetic laboratory experiment. Not this organization's historical performance.")  # noqa: E501
    elif evidence.source_mode == "manual":
        risks.insert(0, "User-defined exploratory model. Not historically calibrated.")
    elif evidence.source_mode == "jira":
        risks.insert(0, "Source-linked Jira evidence. Historical validation is separate from import success.")  # noqa: E501
    elif evidence.source_mode == "csv":
        risks.insert(0, "CSV-uploaded event log. Not independently audited organizational history.")
    if evidence.exploratory:
        risks.append("The baseline is exploratory and is not historically adequate.")
    next_action = "Do not implement on this evidence alone."
    attractive = [
        row.strategy_id
        for row in rows
        if row.decision_state == "economically_attractive_under_current_assumptions"
    ]
    if attractive:
        next_action = (
            f"Under the selected assumptions, {', '.join(attractive)} is economically attractive. "
            "Validate realization mechanisms before any implementation decision."
        )
    elif any(row.decision_state == "suitable_for_controlled_pilot_evaluation" for row in rows):
        next_action = (
            "Operational improvement appears without recovered investment. "
            "A bounded pilot is the strongest action supported by this evidence."
        )
    elif any(row.decision_state == "capacity_releasing_without_cash_savings" for row in rows):
        next_action = (
            "Capacity is released without realizable cash savings under the selected mechanism. "
            "Defer spend unless a cash realization path is approved."
        )
    return DecisionBrief(
        baseline=evidence.fixture_id or "synthetic-baseline",
        strategies=[row.strategy_id for row in rows],
        operational_findings=operational,
        economic_findings=economic,
        key_assumptions=[
            f"Currency {assumptions.currency}, {assumptions.evaluation_months} months, origin {assumptions.origin}.",  # noqa: E501
            f"Staff {assumptions.monthly_staff_cost_per_fte} per FTE-month; realization {assumptions.realization_mechanism} at {assumptions.realization_rate}.",  # noqa: E501
            f"AI subscription {assumptions.ai_subscription_monthly}/month; implementation {assumptions.implementation_cost}.",  # noqa: E501
        ],
        break_even=(
            None
            if break_even is None
            else f"{break_even.parameter}: {break_even.threshold_status}"
            + (f" near {break_even.threshold:.4g}" if break_even.threshold is not None else "")
        ),
        material_risks=risks,
        suggested_next_action=next_action,
    )


def evaluate_decision(request: DecisionEvaluationRequest) -> DecisionEvaluationResult:
    started = perf_counter()
    evidence = request.evidence
    if evidence is None:
        raise DecisionError("invalid_evidence", "Operational evidence is required.")
    if evidence.identities_agree is not True:
        raise DecisionError("invalid_evidence", "Operational evidence failed identity checks.")
    if evidence.contract_version != "cg5.v1":
        raise DecisionError("unsupported_contract", "Economic evaluation requires cg5.v1 evidence.")
    if evidence.experiment_status == "failed":
        raise DecisionError(
            "insufficient_operational_evidence",
            "A failed experiment cannot produce an economic comparison.",
        )
    if evidence.experiment_status == "complete":
        if evidence.integrity_status != "passed":
            raise DecisionError("invalid_evidence", "Complete experiments require passed integrity.")  # noqa: E501
        if any(item.status != "valid" for item in evidence.alternatives):
            raise DecisionError("invalid_evidence", "A complete experiment cannot include failed alternatives.")  # noqa: E501
    expected_ids = [item.alternative_id for item in request.alternatives]
    evidence_ids = [item.alternative_id for item in evidence.alternatives]
    if expected_ids != evidence_ids:
        raise DecisionError("experiment_identity_mismatch", "Alternative identifiers do not match the experiment.")  # noqa: E501
    computed = operational_experiment_identity(
        fixture_id=request.fixture_id,
        model_fingerprint=evidence.calibrated_model_fingerprint,
        alternatives=request.alternatives,
        execution=request.execution,
    )
    if computed != request.experiment_identity or computed != evidence.experiment_identity:
        raise DecisionError(
            "experiment_identity_mismatch",
            "Economic evaluation does not match the operational experiment identity.",
        )
    alternatives_by_id = {item.alternative_id: item for item in request.alternatives}
    baseline_ops = _ops_from_metrics(evidence.baseline_metrics, evidence.baseline_resource_metrics)
    baseline_row = evaluate_strategy_economics(
        strategy_id="baseline",
        kind="baseline",
        alternative=None,
        ops=baseline_ops,
        baseline_ops=baseline_ops,
        assumptions=request.assumptions,
        constraints=request.constraints,
    )
    rows = [baseline_row]
    valid_count = 0
    for item in evidence.alternatives:
        if item.status != "valid":
            continue
        valid_count += 1
        selected = alternatives_by_id[item.alternative_id]
        ops = _ops_from_metrics(item.system_metrics, item.resource_metrics)
        rows.append(
            evaluate_strategy_economics(
                strategy_id=item.alternative_id,
                kind=selected.intervention.kind,
                alternative=selected,
                ops=ops,
                baseline_ops=baseline_ops,
                assumptions=request.assumptions,
                constraints=request.constraints,
            )
        )
    if valid_count == 0:
        raise DecisionError(
            "insufficient_operational_evidence",
            "No valid alternatives are available for economic comparison.",
        )
    rows = _mark_dominated(rows)
    break_even = None
    if request.explore is not None:
        if request.explore.parameter not in FINANCIAL_ONLY:
            raise DecisionError(
                "operational_sensitivity_required",
                "This parameter changes intervention behavior and requires a simulation experiment.",  # noqa: E501
            )
        if request.explore.high < request.explore.low:
            raise DecisionError("invalid_explore_range", "Break-even high must be at least low.")
        requested = request.explore.strategy_id
        focus = next((row for row in rows if row.strategy_id == requested), None)
        if focus is None or focus.strategy_id == "baseline":
            raise DecisionError(
                "invalid_explore_strategy",
                "Break-even exploration requires an explicit non-baseline strategy.",
            )
        if request.explore.parameter in {"aiSubscriptionMonthly", "aiCostPerAutomatedCase"}:
            if not _uses_ai(focus.intervention_kind):
                raise DecisionError(
                    "invalid_explore_parameter",
                    "AI cost sensitivity is not defined for a strategy that does not use AI.",
                )
        named: NamedAlternative | None = alternatives_by_id.get(focus.strategy_id)
        focus_evidence = next(item for item in evidence.alternatives if item.alternative_id == focus.strategy_id)  # noqa: E501
        ops = _ops_from_metrics(focus_evidence.system_metrics, focus_evidence.resource_metrics)
        span = request.explore.high - request.explore.low
        count = request.explore.point_count
        points: list[BreakEvenPoint] = []
        for index in range(count):
            value = request.explore.low + span * index / (count - 1)
            patched = _patch_assumptions(request.assumptions, request.explore.parameter, value)
            economics = evaluate_strategy_economics(
                strategy_id=focus.strategy_id,
                kind=named.intervention.kind if named else focus.intervention_kind,
                alternative=named,
                ops=ops,
                baseline_ops=baseline_ops,
                assumptions=patched,
                constraints=request.constraints,
            )
            points.append(
                BreakEvenPoint(
                    parameter_value=value,
                    net_benefit=economics.net_benefit,
                    roi=economics.roi,
                )
            )
        threshold, status = _threshold(points)
        if status == "one_threshold":
            explanation = (
                f"Approximate financial-only threshold for {request.explore.parameter} "
                f"where net benefit crosses zero, using the same operational means."
            )
        elif status == "no_break_even_in_range":
            explanation = "Net benefit does not change sign in the evaluated financial range."
        else:
            explanation = "A break-even threshold could not be derived from the evaluated points."
        break_even = BreakEvenEvidence(
            parameter=request.explore.parameter,
            mode="financial_only",
            current_value=_current_parameter(request.assumptions, request.explore.parameter),
            points=points,
            threshold=threshold,
            threshold_status=status,
            explanation=explanation,
        )
        if status == "one_threshold":
            rows = [
                row.model_copy(
                    update={"decision_state": "attractive_only_under_break_even_conditions"}
                )
                if row.strategy_id == focus.strategy_id
                and row.decision_state
                in {
                    "operationally_beneficial_financially_unattractive",
                    "not_justified_under_the_selected_assumptions",
                    "suitable_for_controlled_pilot_evaluation",
                }
                else row
                for row in rows
            ]
        signs = {point.net_benefit is not None and point.net_benefit >= 0 for point in points}
        if True in signs and False in signs:
            rows = [
                row.model_copy(update={"decision_state": "high_sensitivity_to_uncertain_assumptions"})  # noqa: E501
                if row.strategy_id == focus.strategy_id
                else row
                for row in rows
            ]
    assumption_id = economic_assumption_identity(request.assumptions.model_dump(by_alias=True))
    evaluation_id = economic_evaluation_identity(
        computed,
        assumption_id,
        constraints=request.constraints.model_dump(by_alias=True, exclude_none=True),
        explore=None
        if request.explore is None
        else request.explore.model_dump(by_alias=True),
        selected_strategy=None if request.explore is None else request.explore.strategy_id,
    )
    duration_ms = int((perf_counter() - started) * 1000)
    return DecisionEvaluationResult(
        fixture_id=request.fixture_id,
        operational_experiment_identity=computed,
        economic_assumption_identity=assumption_id,
        economic_evaluation_identity=evaluation_id,
        measurement_mode=request.assumptions.evaluation_basis,
        synthetic=evidence.synthetic,
        economic_uncertainty="conditional_on_summarized_operational_outcomes",
        integrity_status="passed",
        experiment_status="complete" if evidence.experiment_status == "complete" else "partial",
        historically_adequate=evidence.historically_adequate,
        exploratory=evidence.exploratory,
        strategies=rows,
        break_even=break_even,
        brief=_brief(evidence, rows, request.assumptions, break_even),
        duration_ms=duration_ms,
        disclosures=[
            "Decision arithmetic is deterministic and does not use an LLM.",
            "Released capacity is not labeled as eliminated jobs.",
            "ROI is unavailable when incremental investment is zero.",
            *evidence.disclosures[:6],
        ],
    )
