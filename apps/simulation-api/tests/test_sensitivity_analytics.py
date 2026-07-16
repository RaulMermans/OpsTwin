from app.sensitivity.analytics import (
    classify_monotonicity,
    finite_differences,
    observed_elasticity,
    threshold_crossings,
)


def test_finite_differences_use_only_adjacent_successful_points() -> None:
    points = [(1.0, 10.0), (2.0, 8.0), (3.0, None), (4.0, 7.0)]

    differences = finite_differences("averageCycleTime", "minutes", points)

    assert len(differences) == 1
    assert differences[0].finite_difference == -2.0


def test_observed_elasticity_applies_null_rules() -> None:
    assert observed_elasticity(2, 10, 4, 5) == -0.5
    assert observed_elasticity(0, 10, 1, 5) is None
    assert observed_elasticity(2, 0, 4, 5) is None
    assert observed_elasticity(2, 10, 2, 5) is None


def test_monotonicity_is_tolerance_aware_and_reports_mixed() -> None:
    assert classify_monotonicity([1.0, 1.0 + 1e-10, 2.0]) == "observed_increasing"
    assert classify_monotonicity([3.0, 2.0, 1.0]) == "observed_decreasing"
    assert classify_monotonicity([1.0, 2.0, 1.5]) == "observed_mixed"
    assert classify_monotonicity([2.0, 2.0, 2.0]) == "observed_flat"
    assert classify_monotonicity([2.0]) == "insufficient_evidence"


def test_threshold_crossings_are_adjacent_and_not_interpolated() -> None:
    points = [(1.0, 0.8), (2.0, 0.9), (3.0, 0.95), (4.0, None), (5.0, 0.7)]

    crossings = threshold_crossings("slaAttainment", "greaterThanOrEqual", 0.9, points)

    assert len(crossings) == 1
    assert crossings[0].lower_parameter_value == 1.0
    assert crossings[0].upper_parameter_value == 2.0
    assert crossings[0].direction == "entered_compliance"


def test_threshold_crossings_report_exit_and_failed_point_interruption() -> None:
    assert (
        threshold_crossings(
            "averageCycleTime",
            "lessThanOrEqual",
            10,
            [(1.0, 9.0), (2.0, 11.0)],
        )[0].direction
        == "left_compliance"
    )
    assert (
        threshold_crossings(
            "averageCycleTime",
            "lessThanOrEqual",
            10,
            [(1.0, 9.0), (2.0, None), (3.0, 11.0)],
        )
        == []
    )
