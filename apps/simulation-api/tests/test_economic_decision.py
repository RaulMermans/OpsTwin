from __future__ import annotations

import pytest

from app.domain.decision import DecisionAssumptions, DecisionConstraints
from app.economics.decision import (
    DecisionError,
    DecisionEvaluationRequest,
    evaluate_decision,
    evaluate_strategy_economics,
)
from app.interventions.catalog import (
    AssistedIntervention,
    CapacityIntervention,
    ExperimentExecution,
    HybridIntervention,
    NamedAlternative,
)
from app.interventions.execute import AlternativeEvidence, MultiExperimentEvidence, PackedMetric
from app.interventions.identity import operational_experiment_identity


def packed(mean: float, unit: str) -> PackedMetric:
    return PackedMetric(mean=mean, p50=mean, lower=mean, upper=mean, unit=unit)


def evidence_for(
    alternatives: list[NamedAlternative],
    rows: dict[str, dict[str, float]],
    *,
    status: str = "complete",
    integrity: str = "passed",
) -> tuple[str, MultiExperimentEvidence]:
    execution = ExperimentExecution(item_count=20, run_count=2, base_seed=20261127)
    fingerprint = "a" * 64
    identity = operational_experiment_identity(
        fixture_id="cg5-hybrid-support",
        model_fingerprint=fingerprint,
        alternatives=alternatives,
        execution=execution,
    )
    packed_alts = []
    for item in alternatives:
        metrics = rows[item.alternative_id]
        packed_alts.append(
            AlternativeEvidence(
                alternative_id=item.alternative_id,
                intervention_kind=item.intervention.kind,
                intervention_name=item.intervention.kind,
                intervention=item.intervention.model_dump(by_alias=True),
                status="valid",
                system_metrics={
                    "averageCycleTime": packed(metrics["cycle"], "minutes"),
                    "completedItems": packed(metrics["completions"], "items"),
                    "terminallyFailedItems": packed(0, "items"),
                },
                resource_metrics={
                    "triage-team": {"busyTime": packed(metrics["busy_minutes"], "minutes")}
                },
            )
        )
    baseline = rows["baseline"]
    evidence = MultiExperimentEvidence(
        fixture_id="cg5-hybrid-support",
        experiment_id="lab",
        experiment_identity=identity,
        experiment_status=status,  # type: ignore[arg-type]
        approximations=[],
        baseline_readiness="model_constructed",
        baseline_class="constructed_exploratory",
        historically_adequate=False,
        exploratory=True,
        disclosures=["synthetic"],
        baseline_inventory={"triageCapacity": 1, "resolutionCapacity": 1},
        calibrated_model_fingerprint=fingerprint,
        executed_model_fingerprint=fingerprint,
        identities_agree=True,
        experiment=execution,
        baseline_metrics={
            "averageCycleTime": packed(baseline["cycle"], "minutes"),
            "completedItems": packed(baseline["completions"], "items"),
            "terminallyFailedItems": packed(0, "items"),
        },
        baseline_resource_metrics={
            "triage-team": {"busyTime": packed(baseline["busy_minutes"], "minutes")}
        },
        alternatives=packed_alts,
        integrity_status=integrity,
        improvement_interpretation="paired",
    )
    return identity, evidence


ALTERNATIVES = [
    NamedAlternative(
        alternative_id="human-expansion",
        intervention=CapacityIntervention(extra_triage_capacity=0, extra_resolution_capacity=1),
    ),
    NamedAlternative(
        alternative_id="ai-assisted",
        intervention=AssistedIntervention(),
    ),
    NamedAlternative(
        alternative_id="hybrid",
        intervention=HybridIntervention(),
    ),
]

ROWS = {
    "baseline": {"cycle": 17.61, "completions": 20, "busy_minutes": 72_000},
    "human-expansion": {"cycle": 17.61, "completions": 20, "busy_minutes": 72_000},
    "ai-assisted": {"cycle": 16.707, "completions": 20, "busy_minutes": 60_000},
    "hybrid": {"cycle": 14.139, "completions": 20, "busy_minutes": 12_000},
}


def test_released_hours_are_not_cash_when_realization_is_none() -> None:
    assumptions = DecisionAssumptions(
        monthly_staff_cost_per_fte=1_000,
        evaluation_basis="fixed_workload",
        evaluation_months=12,
        realization_mechanism="none",
        realization_rate=0,
        ai_subscription_monthly=500,
        implementation_cost=2_000,
    )
    identity, evidence = evidence_for(ALTERNATIVES, ROWS)
    result = evaluate_decision(
        DecisionEvaluationRequest(
            fixture_id="cg5-hybrid-support",
            alternatives=ALTERNATIVES,
            execution=evidence.experiment,
            experiment_identity=identity,
            evidence=evidence,
            assumptions=assumptions,
        )
    )
    hybrid = next(item for item in result.strategies if item.strategy_id == "hybrid")
    human = next(item for item in result.strategies if item.strategy_id == "human-expansion")
    assert hybrid.released_human_hours == pytest.approx(1_000)
    assert hybrid.realizable_cash_benefit == 0
    assert hybrid.roi is None
    assert hybrid.payback_status == "not_applicable"
    assert human.incremental_staffing_cost == pytest.approx(0)
    assert human.average_cycle_time == pytest.approx(17.61)
    baseline = next(item for item in result.strategies if item.strategy_id == "baseline")
    assert baseline.roi is None
    assert baseline.incremental_investment == 0


def test_known_roi_and_payback_with_explicit_realization() -> None:
    # Independent golden: demand 20 cases/month, 12 months, simulated 20 completions → scale 12.
    # Released hours 1000 × 12 = 12000; hourly 1600/160 = 10; realizable = 120000.
    # AI subscription 500×12 = 6000; implementation 2000; incremental investment 8000.
    # Net 112000; ROI 14; payback 2000 / ((120000-6000)/12) = 0.210526 months.
    assumptions = DecisionAssumptions(
        monthly_staff_cost_per_fte=1_600,
        paid_hours_per_month=160,
        evaluation_basis="recurring_period",
        expected_demand_per_month=20,
        evaluation_months=12,
        realization_mechanism="avoided_hiring",
        realization_rate=1,
        ai_subscription_monthly=500,
        implementation_cost=2_000,
        value_released_capacity=True,
    )
    identity, evidence = evidence_for(ALTERNATIVES, ROWS)
    result = evaluate_decision(
        DecisionEvaluationRequest(
            fixture_id="cg5-hybrid-support",
            alternatives=ALTERNATIVES,
            execution=evidence.experiment,
            experiment_identity=identity,
            evidence=evidence,
            assumptions=assumptions,
        )
    )
    hybrid = next(item for item in result.strategies if item.strategy_id == "hybrid")
    assert hybrid.released_human_hours == pytest.approx(12_000)
    assert hybrid.realizable_cash_benefit == pytest.approx(120_000)
    assert hybrid.incremental_investment == pytest.approx(8_000)
    assert hybrid.net_benefit == pytest.approx(112_000)
    assert hybrid.roi == pytest.approx(14)
    assert hybrid.payback_status == "recovered_within_horizon"
    assert hybrid.payback_months == pytest.approx(2_000 / 9_500)
    assert hybrid.potential_capacity_value == pytest.approx(120_000)


def test_break_even_subscription_matches_hand_calculation() -> None:
    assumptions = DecisionAssumptions(
        monthly_staff_cost_per_fte=1_600,
        paid_hours_per_month=160,
        evaluation_basis="recurring_period",
        expected_demand_per_month=20 / 12,
        evaluation_months=12,
        realization_mechanism="avoided_hiring",
        realization_rate=1,
        ai_subscription_monthly=900,
        implementation_cost=2_000,
    )
    identity, evidence = evidence_for(
        [ALTERNATIVES[2]],
        {"baseline": ROWS["baseline"], "hybrid": ROWS["hybrid"]},
    )
    result = evaluate_decision(
        DecisionEvaluationRequest(
            fixture_id="cg5-hybrid-support",
            alternatives=[ALTERNATIVES[2]],
            execution=evidence.experiment,
            experiment_identity=identity,
            evidence=evidence,
            assumptions=assumptions,
            explore={
                "strategyId": "hybrid",
                "parameter": "aiSubscriptionMonthly",
                "low": 0,
                "high": 1_000,
                "pointCount": 5,
            },
        )
    )
    assert result.break_even is not None
    assert result.break_even.reused_operational_evidence is True
    assert result.break_even.threshold_status == "one_threshold"
    assert result.break_even.threshold == pytest.approx(666.666, rel=0.05)


def test_failed_and_invalid_integrity_cannot_rank() -> None:
    identity, evidence = evidence_for(ALTERNATIVES, ROWS, status="failed")
    with pytest.raises(DecisionError, match="failed experiment"):
        evaluate_decision(
            DecisionEvaluationRequest(
                fixture_id="cg5-hybrid-support",
                alternatives=ALTERNATIVES,
                execution=evidence.experiment,
                experiment_identity=identity,
                evidence=evidence,
                assumptions=DecisionAssumptions(),
            )
        )
    identity, evidence = evidence_for(ALTERNATIVES, ROWS, integrity="failed")
    with pytest.raises(DecisionError, match="passed integrity"):
        evaluate_decision(
            DecisionEvaluationRequest(
                fixture_id="cg5-hybrid-support",
                alternatives=ALTERNATIVES,
                execution=evidence.experiment,
                experiment_identity=identity,
                evidence=evidence,
                assumptions=DecisionAssumptions(),
            )
        )


def test_coverage_change_changes_operational_identity() -> None:
    execution = ExperimentExecution(item_count=20, run_count=2)
    left = operational_experiment_identity(
        fixture_id="cg5-hybrid-support",
        model_fingerprint="b" * 64,
        alternatives=[ALTERNATIVES[1]],
        execution=execution,
    )
    right = operational_experiment_identity(
        fixture_id="cg5-hybrid-support",
        model_fingerprint="b" * 64,
        alternatives=[
            NamedAlternative(
                alternative_id="ai-assisted",
                intervention=AssistedIntervention(coverage=0.75),
            )
        ],
        execution=execution,
    )
    assert left != right


def test_zero_investment_does_not_invent_roi() -> None:
    assumptions = DecisionAssumptions(
        monthly_staff_cost_per_fte=1_000,
        ai_subscription_monthly=0,
        implementation_cost=0,
        realization_mechanism="none",
    )
    row = evaluate_strategy_economics(
        strategy_id="ai-assisted",
        kind="ai_assisted",
        alternative=ALTERNATIVES[1],
        ops={"completions": 20, "cycle": 16, "unsuccessful": 0, "busy_hours": 10},
        baseline_ops={"completions": 20, "cycle": 17, "unsuccessful": 0, "busy_hours": 12},
        assumptions=assumptions,
        constraints=DecisionConstraints(),
    )
    assert row.incremental_investment == 0
    assert row.roi is None
    assert row.realizable_cash_benefit == 0
