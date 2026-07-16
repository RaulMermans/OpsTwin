import math

import pytest

from app.domain.repeated import RiskThresholds
from app.engine.aggregation import (
    RepresentativeCandidate,
    RunningMoments,
    aggregate_metric,
    evaluate_risks,
    nearest_rank,
    select_representative,
)


def test_gm021_welford_moments_match_hand_calculation() -> None:
    moments = RunningMoments()
    for value in [1.0, 2.0, 3.0, 4.0]:
        moments.add(value)

    assert moments.count == 4
    assert moments.mean == 2.5
    assert moments.sample_variance == pytest.approx(5 / 3)
    assert moments.standard_deviation == pytest.approx(math.sqrt(5 / 3))
    assert moments.minimum == 1
    assert moments.maximum == 4


def test_gm022_nearest_rank_quantiles_are_exact() -> None:
    values = list(range(1, 11))

    assert nearest_rank(values, 0.10) == 1
    assert nearest_rank(values, 0.50) == 5
    assert nearest_rank(values, 0.90) == 9


def test_gm023_normal_confidence_interval_is_documented_approximation() -> None:
    aggregate = aggregate_metric([1.0, 2.0, 3.0, 4.0], 0.95)
    standard_error = math.sqrt(5 / 3) / 2
    margin = 1.959964 * standard_error

    assert aggregate.mean == 2.5
    assert aggregate.confidence_interval.lower == pytest.approx(2.5 - margin)
    assert aggregate.confidence_interval.upper == pytest.approx(2.5 + margin)
    assert aggregate.confidence_interval.method == "normal_approximation"
    assert aggregate.confidence_interval.reliable_sample_size is False


def test_confidence_interval_marks_thirty_samples_reliable() -> None:
    aggregate = aggregate_metric([float(value) for value in range(30)], 0.90)

    assert aggregate.confidence_interval.reliable_sample_size is True
    assert aggregate.p10 == 2
    assert aggregate.p50 == 14
    assert aggregate.p90 == 26


def test_gm024_risk_probability_uses_valid_runs_only() -> None:
    risks = evaluate_risks(
        {
            "slaAttainment": [0.8, 0.9, 0.95, 0.7],
            "averageCycleTime": [10, 20, 30, 40],
        },
        RiskThresholds(
            minimumSlaAttainment=0.9,
            maximumAverageCycleTime=25,
        ),
    )

    assert [(risk.metric, risk.violating_runs, risk.probability) for risk in risks] == [
        ("slaAttainment", 2, 0.5),
        ("averageCycleTime", 2, 0.5),
    ]


def test_gm024_omitted_thresholds_produce_no_results() -> None:
    assert evaluate_risks({"slaAttainment": [0.5, 1.0]}, RiskThresholds()) == []


def test_gm025_representative_uses_normalized_median_vector_and_index_tie() -> None:
    candidates = [
        RepresentativeCandidate(0, 100, {"a": 0.0, "b": 10.0}),
        RepresentativeCandidate(1, 101, {"a": 5.0, "b": 5.0}),
        RepresentativeCandidate(2, 102, {"a": 10.0, "b": 0.0}),
        RepresentativeCandidate(3, 103, {"a": 5.0, "b": 5.0}),
    ]

    selection = select_representative(candidates)

    assert selection.candidate.run_index == 1
    assert selection.median_vector == {"a": 5.0, "b": 5.0}
    assert selection.distance == 0


def test_representative_zero_range_dimension_contributes_zero() -> None:
    selection = select_representative(
        [
            RepresentativeCandidate(0, 100, {"a": 1.0, "b": 0.0}),
            RepresentativeCandidate(1, 101, {"a": 1.0, "b": 2.0}),
        ]
    )

    assert selection.candidate.run_index == 0
