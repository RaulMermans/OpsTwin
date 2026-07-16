from __future__ import annotations

from math import isfinite

from app.domain.sensitivity import SensitivityRequest, SensitivityResult


class SensitivityIntegrityError(RuntimeError):
    """Raised when sensitivity evidence does not reconcile internally."""


def validate_sensitivity_integrity(request: SensitivityRequest, result: SensitivityResult) -> int:
    checks = [
        (result.schema_version == "0.6.0", "schema version differs"),
        (result.canonical_values == sorted(result.canonical_values), "values not sorted"),
        (len(result.canonical_values) == len(set(result.canonical_values)), "duplicate values"),
        (result.target.baseline_value in result.canonical_values, "baseline value missing"),
        (len(result.values) == len(result.canonical_values), "value result count differs"),
        (
            [item.parameter_value for item in result.values] == result.canonical_values,
            "value order differs",
        ),
        (
            sum(item.is_baseline_value for item in result.values) == 1,
            "baseline marker count differs",
        ),
        (
            next(item for item in result.values if item.is_baseline_value).status == "valid",
            "baseline failed",
        ),
        (len(result.run_seeds) == request.execution.run_count, "seed count differs"),
        (
            [item.run_index for item in result.run_seeds]
            == list(range(request.execution.run_count)),
            "seed indexes differ",
        ),
        (
            len({item.seed for item in result.run_seeds}) == len(result.run_seeds),
            "run seeds repeat",
        ),
        (
            result.work_budget.estimated_work_units
            == result.work_budget.baseline_item_count
            * result.work_budget.run_count
            * result.work_budget.tested_value_count,
            "work formula differs",
        ),
        (
            result.work_budget.estimated_work_units <= result.work_budget.maximum_work_units,
            "work budget exceeded",
        ),
        (result.execution.execution_order == "run_index_then_values", "execution order differs"),
        (
            result.execution.ordinary_run_included_event_count == 0,
            "ordinary included events nonzero",
        ),
        (
            result.execution.ordinary_run_retained_event_count == 0,
            "ordinary retained events nonzero",
        ),
        (len(result.response_curves) == len(request.metrics), "curve count differs"),
        (
            [curve.metric for curve in result.response_curves] == request.metrics,
            "curve metric order differs",
        ),
        (
            all(len(curve.points) == len(result.values) for curve in result.response_curves),
            "curve point count differs",
        ),
        (
            all(
                [point.parameter_value for point in curve.points] == result.canonical_values
                for curve in result.response_curves
            ),
            "curve point order differs",
        ),
        (
            all(
                point.mean is None or isfinite(point.mean)
                for curve in result.response_curves
                for point in curve.points
            ),
            "non-finite point mean",
        ),
        (
            all(
                point.observed_elasticity is None or isfinite(point.observed_elasticity)
                for curve in result.response_curves
                for point in curve.points
            ),
            "non-finite elasticity",
        ),
        (
            all(item.model_hash is not None for item in result.values if item.status == "valid"),
            "valid value hash missing",
        ),
        (
            all(item.paired_run_count <= request.execution.run_count for item in result.values),
            "paired count exceeds request",
        ),
    ]
    for passed, message in checks:
        if not passed:
            raise SensitivityIntegrityError(message)
    return len(checks)
