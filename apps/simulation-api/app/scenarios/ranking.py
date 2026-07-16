from __future__ import annotations

from dataclasses import dataclass

from app.domain.comparison import (
    OBJECTIVE_DIRECTIONS,
    ComparisonGuardrail,
)


@dataclass(frozen=True)
class GuardrailResult:
    metric: str
    operator: str
    threshold: float
    observed_value: float
    statistic: str
    passed: bool
    resource_pool_id: str | None


@dataclass(frozen=True)
class RankingCandidate:
    scenario_id: str
    comparison_valid: bool
    guardrails_passed: bool
    objective_mean_delta: float
    probability_of_improvement: float
    confidence_interval_width: float


@dataclass(frozen=True)
class RankingRow:
    rank: int | None
    scenario_id: str
    eligible: bool
    guardrails_passed: bool
    objective_metric: str
    objective_mean_delta: float
    probability_of_improvement: float
    confidence_interval_width: float
    tie_break_explanation: str


def evaluate_guardrails(
    guardrails: list[ComparisonGuardrail],
    *,
    system_means: dict[str, float],
    resource_means: dict[str, dict[str, float]],
) -> list[GuardrailResult]:
    results: list[GuardrailResult] = []
    for guardrail in guardrails:
        if guardrail.metric == "resourcePoolUtilization":
            assert guardrail.resource_pool_id is not None
            observed = resource_means[guardrail.resource_pool_id]["utilization"]
        else:
            observed = system_means[guardrail.metric]
        passed = (
            observed <= guardrail.value
            if guardrail.operator == "lessThanOrEqual"
            else observed >= guardrail.value
        )
        results.append(
            GuardrailResult(
                metric=guardrail.metric,
                operator=guardrail.operator,
                threshold=guardrail.value,
                observed_value=observed,
                statistic="mean",
                passed=passed,
                resource_pool_id=guardrail.resource_pool_id,
            )
        )
    return results


def rank_candidates(
    candidates: list[RankingCandidate], *, objective_metric: str
) -> list[RankingRow]:
    direction = OBJECTIVE_DIRECTIONS[objective_metric]
    eligible = [
        candidate
        for candidate in candidates
        if candidate.comparison_valid and candidate.guardrails_passed
    ]
    ordered = sorted(
        eligible,
        key=lambda candidate: (
            -candidate.objective_mean_delta
            if direction == "maximize"
            else candidate.objective_mean_delta,
            -candidate.probability_of_improvement,
            candidate.confidence_interval_width,
            candidate.scenario_id,
        ),
    )
    ranks = {candidate.scenario_id: index + 1 for index, candidate in enumerate(ordered)}
    rows = [
        RankingRow(
            rank=ranks[candidate.scenario_id],
            scenario_id=candidate.scenario_id,
            eligible=True,
            guardrails_passed=True,
            objective_metric=objective_metric,
            objective_mean_delta=candidate.objective_mean_delta,
            probability_of_improvement=candidate.probability_of_improvement,
            confidence_interval_width=candidate.confidence_interval_width,
            tie_break_explanation=(
                "directed mean delta, improvement probability, confidence width, scenario ID"
            ),
        )
        for candidate in ordered
    ]
    rows.extend(
        RankingRow(
            rank=None,
            scenario_id=candidate.scenario_id,
            eligible=False,
            guardrails_passed=candidate.guardrails_passed,
            objective_metric=objective_metric,
            objective_mean_delta=candidate.objective_mean_delta,
            probability_of_improvement=candidate.probability_of_improvement,
            confidence_interval_width=candidate.confidence_interval_width,
            tie_break_explanation=(
                "ineligible because comparison is invalid"
                if not candidate.comparison_valid
                else "ineligible because a guardrail failed"
            ),
        )
        for candidate in sorted(candidates, key=lambda item: item.scenario_id)
        if candidate.scenario_id not in ranks
    )
    return rows
