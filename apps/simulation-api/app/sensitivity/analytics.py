from __future__ import annotations

from math import isfinite
from typing import Literal

from app.domain.sensitivity import FiniteDifference, ThresholdCrossing
from app.scenarios.metrics import FLOAT_COMPARISON_TOLERANCE

Monotonicity = Literal[
    "observed_increasing",
    "observed_decreasing",
    "observed_flat",
    "observed_mixed",
    "insufficient_evidence",
]


def finite_differences(
    metric: str, unit: str, points: list[tuple[float, float | None]]
) -> list[FiniteDifference]:
    results: list[FiniteDifference] = []
    for (lower_x, lower_y), (upper_x, upper_y) in zip(points, points[1:], strict=False):
        if lower_y is None or upper_y is None:
            continue
        parameter_difference = upper_x - lower_x
        metric_difference = upper_y - lower_y
        results.append(
            FiniteDifference(
                metric=metric,
                unit=unit,
                lower_parameter_value=lower_x,
                upper_parameter_value=upper_x,
                parameter_difference=parameter_difference,
                metric_difference=metric_difference,
                finite_difference=metric_difference / parameter_difference,
            )
        )
    return results


def observed_elasticity(
    baseline_parameter: float,
    baseline_metric: float,
    parameter: float,
    metric: float,
) -> float | None:
    values = (baseline_parameter, baseline_metric, parameter, metric)
    if not all(isfinite(value) for value in values):
        return None
    if baseline_parameter == 0 or baseline_metric == 0 or parameter == baseline_parameter:
        return None
    parameter_change = (parameter - baseline_parameter) / abs(baseline_parameter)
    if parameter_change == 0:
        return None
    value = ((metric - baseline_metric) / abs(baseline_metric)) / parameter_change
    return value if isfinite(value) else None


def classify_monotonicity(values: list[float]) -> Monotonicity:
    if len(values) < 2:
        return "insufficient_evidence"
    directions: set[int] = set()
    for lower, upper in zip(values, values[1:], strict=False):
        delta = upper - lower
        if abs(delta) <= FLOAT_COMPARISON_TOLERANCE:
            continue
        directions.add(1 if delta > 0 else -1)
    if not directions:
        return "observed_flat"
    if directions == {1}:
        return "observed_increasing"
    if directions == {-1}:
        return "observed_decreasing"
    return "observed_mixed"


def threshold_crossings(
    metric: str,
    operator: Literal["greaterThanOrEqual", "lessThanOrEqual"],
    threshold: float,
    points: list[tuple[float, float | None]],
) -> list[ThresholdCrossing]:
    def compliant(value: float) -> bool:
        return value >= threshold if operator == "greaterThanOrEqual" else value <= threshold

    results: list[ThresholdCrossing] = []
    for (lower_x, lower_y), (upper_x, upper_y) in zip(points, points[1:], strict=False):
        if lower_y is None or upper_y is None:
            continue
        lower_ok = compliant(lower_y)
        upper_ok = compliant(upper_y)
        if lower_ok == upper_ok:
            continue
        results.append(
            ThresholdCrossing(
                metric=metric,
                operator=operator,
                threshold=threshold,
                lower_parameter_value=lower_x,
                upper_parameter_value=upper_x,
                lower_observed_metric=lower_y,
                upper_observed_metric=upper_y,
                direction="entered_compliance" if upper_ok else "left_compliance",
            )
        )
    return results
