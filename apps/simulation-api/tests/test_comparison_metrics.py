import math

import pytest

from app.scenarios.metrics import (
    FLOAT_COMPARISON_TOLERANCE,
    METRIC_REGISTRY,
    compare_paired_metric,
    compare_threshold_risk,
)


def test_gm034_paired_delta_aggregation_is_exact() -> None:
    result = compare_paired_metric(
        {0: 10.0, 1: 20.0, 2: 30.0, 3: 40.0},
        {0: 8.0, 1: 18.0, 2: 33.0, 3: 44.0},
        metric="averageCycleTime",
        confidence_level=0.95,
    )

    assert result.paired_run_indexes == [0, 1, 2, 3]
    assert result.deltas == [-2.0, -2.0, 3.0, 4.0]
    assert result.absolute.count == 4
    assert result.absolute.mean == 0.75
    assert result.absolute.sample_variance == pytest.approx(10.25)
    assert result.absolute.standard_deviation == pytest.approx(math.sqrt(10.25))
    assert (result.absolute.p10, result.absolute.p50, result.absolute.p90) == (-2, -2, 4)
    assert result.absolute.confidence_interval.lower == pytest.approx(-2.387473248223959)
    assert result.absolute.confidence_interval.upper == pytest.approx(3.887473248223959)
    assert result.relative is not None
    assert result.relative.mean == pytest.approx(-0.025)
    assert result.relative_delta_undefined_count == 0


@pytest.mark.parametrize(
    ("metric", "improved", "degraded", "tied"),
    [
        ("slaAttainment", 1, 1, 1),
        ("averageCycleTime", 1, 1, 1),
    ],
)
def test_gm035_improvement_probability_uses_metric_direction(
    metric: str, improved: int, degraded: int, tied: int
) -> None:
    result = compare_paired_metric(
        {0: 1.0, 1: 2.0, 2: 3.0},
        {0: 2.0, 1: 2.0 + FLOAT_COMPARISON_TOLERANCE / 2, 2: 2.0},
        metric=metric,
        confidence_level=0.95,
    )

    assert result.improvement.improved_count == improved
    assert result.improvement.degraded_count == degraded
    assert result.improvement.tied_count == tied
    assert result.improvement.probability_of_improvement == pytest.approx(1 / 3)
    assert result.improvement.valid_paired_run_count == 3


def test_gm036_zero_baseline_relative_delta_is_null_and_counted() -> None:
    result = compare_paired_metric(
        {0: 0.0, 1: 2.0},
        {0: 2.0, 1: 4.0},
        metric="completionRate",
        confidence_level=0.95,
    )

    assert result.relative_deltas == [None, 1.0]
    assert result.relative_delta_undefined_count == 1
    assert result.relative is not None
    assert result.relative.count == 1
    assert result.relative.mean == 1


def test_risk_comparison_quadrants_reconcile() -> None:
    result = compare_threshold_risk(
        {0: 5.0, 1: 15.0, 2: 15.0, 3: 5.0},
        {0: 5.0, 1: 5.0, 2: 15.0, 3: 15.0},
        metric="averageCycleTime",
        operator="above",
        threshold=10,
    )

    assert result.baseline_probability == 0.5
    assert result.scenario_probability == 0.5
    assert result.probability_point_change == 0
    assert result.relative_change == 0
    assert (
        result.baseline_only_violates,
        result.scenario_only_violates,
        result.both_violate,
        result.neither_violates,
    ) == (1, 1, 1, 1)


def test_metric_registry_centralizes_contextual_utilization() -> None:
    metadata = METRIC_REGISTRY["resourcePoolUtilization"]

    assert metadata.direction == "contextual"
    assert metadata.objective_eligible is False
    assert metadata.guardrail_operators == ("lessThanOrEqual",)
