from app.domain.comparison import ComparisonGuardrail
from app.scenarios.ranking import (
    RankingCandidate,
    evaluate_guardrails,
    rank_candidates,
)


def candidate(
    scenario_id: str,
    mean_delta: float,
    probability: float,
    width: float,
    *,
    guardrails_passed: bool = True,
) -> RankingCandidate:
    return RankingCandidate(
        scenario_id=scenario_id,
        comparison_valid=True,
        guardrails_passed=guardrails_passed,
        objective_mean_delta=mean_delta,
        probability_of_improvement=probability,
        confidence_interval_width=width,
    )


def test_gm038_ranking_uses_all_deterministic_tie_breakers() -> None:
    ranked = rank_candidates(
        [
            candidate("worse-objective", -1, 0.99, 0.1),
            candidate("low-probability", -2, 0.7, 1),
            candidate("wide", -2, 0.8, 2),
            candidate("z-id", -2, 0.8, 1),
            candidate("a-id", -2, 0.8, 1),
            candidate("guardrail-failed", -5, 1, 0.1, guardrails_passed=False),
        ],
        objective_metric="averageCycleTime",
    )

    assert [row.scenario_id for row in ranked if row.rank is not None] == [
        "a-id",
        "z-id",
        "wide",
        "low-probability",
        "worse-objective",
    ]
    failed = next(row for row in ranked if row.scenario_id == "guardrail-failed")
    assert failed.eligible is False
    assert failed.rank is None
    assert "guardrail" in failed.tie_break_explanation


def test_guardrails_use_scenario_aggregate_mean() -> None:
    results = evaluate_guardrails(
        [
            ComparisonGuardrail(
                metric="averageCycleTime",
                operator="lessThanOrEqual",
                value=10,
            ),
            ComparisonGuardrail(
                metric="slaAttainment",
                operator="greaterThanOrEqual",
                value=0.9,
            ),
        ],
        system_means={"averageCycleTime": 9.5, "slaAttainment": 0.85},
        resource_means={},
    )

    assert [result.passed for result in results] == [True, False]
    assert results[0].statistic == "mean"
