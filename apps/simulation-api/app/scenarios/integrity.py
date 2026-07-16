from __future__ import annotations

import math

from app.domain.comparison import ScenarioComparisonRequest, ScenarioComparisonResult
from app.engine.seed_schedule import seed_schedule
from app.engine.snapshots import MetricSnapshot


class ComparisonIntegrityError(RuntimeError):
    """Raised when calculated comparison evidence does not reconcile."""


def validate_comparison_integrity(
    request: ScenarioComparisonRequest,
    result: ScenarioComparisonResult,
    baseline_snapshots: dict[int, MetricSnapshot],
    scenario_snapshots: dict[str, dict[int, MetricSnapshot]],
) -> int:
    checks = 0

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ComparisonIntegrityError(message)

    require(
        result.baseline_model_hash == result.baseline.model_hash,
        "baseline hash changed",
    )
    checks += 1
    scenario_ids = [scenario.scenario_id for scenario in result.scenarios]
    require(len(scenario_ids) == len(set(scenario_ids)), "scenario IDs repeat")
    checks += 1
    require(
        [seed.seed for seed in result.run_seeds]
        == seed_schedule(request.execution.base_seed, request.execution.run_count),
        "paired seed schedule differs",
    )
    checks += 1
    require(
        all(
            snapshot.run_index == index
            and snapshot.seed == result.run_seeds[index].seed
            for index, snapshot in baseline_snapshots.items()
        ),
        "baseline snapshot index or seed differs",
    )
    checks += 1
    require(
        all(
            snapshot.run_index == index
            and snapshot.seed == result.run_seeds[index].seed
            for snapshots in scenario_snapshots.values()
            for index, snapshot in snapshots.items()
        ),
        "scenario snapshot index or seed differs",
    )
    checks += 1
    for scenario in result.scenarios:
        snapshots = scenario_snapshots.get(scenario.scenario_id, {})
        intersection = sorted(set(baseline_snapshots) & set(snapshots))
        require(
            scenario.paired_run_indexes == intersection
            and scenario.paired_run_count == len(intersection),
            "paired successful intersection differs",
        )
        if scenario.status == "valid":
            for metric, comparison in scenario.paired_metrics.items():
                expected = sum(
                    snapshots[index].system[metric]
                    - baseline_snapshots[index].system[metric]
                    for index in intersection
                ) / len(intersection)
                require(
                    math.isclose(comparison.absolute_delta.mean, expected, abs_tol=1e-12),
                    "paired delta differs from scenario minus baseline",
                )
                improvement = comparison.improvement
                require(
                    improvement.improved_count
                    + improvement.degraded_count
                    + improvement.tied_count
                    == len(intersection),
                    "improvement counts do not reconcile",
                )
            for resource_id, utilization_comparison in (
                scenario.resource_utilization_deltas.items()
            ):
                expected = sum(
                    snapshots[index].resources[resource_id]["utilization"]
                    - baseline_snapshots[index].resources[resource_id]["utilization"]
                    for index in intersection
                ) / len(intersection)
                require(
                    math.isclose(
                        utilization_comparison.absolute_delta.mean,
                        expected,
                        abs_tol=1e-12,
                    ),
                    "paired resource utilization delta differs",
                )
            require(
                all(
                    risk.baseline_only_violates
                    + risk.scenario_only_violates
                    + risk.both_violate
                    + risk.neither_violates
                    == len(intersection)
                    for risk in scenario.risk_comparisons
                ),
                "risk quadrant counts do not reconcile",
            )
    checks += 3
    eligible_ids = {scenario.scenario_id for scenario in result.scenarios if scenario.eligible}
    require(
        {row.scenario_id for row in result.ranking} <= eligible_ids,
        "ranking contains an ineligible scenario",
    )
    checks += 1
    require(
        all(
            scenario.eligible == all(item.passed for item in scenario.guardrails)
            for scenario in result.scenarios
            if scenario.status == "valid"
        ),
        "guardrail eligibility differs",
    )
    checks += 1
    representatives = [
        value
        for value in (result.representatives.baseline, result.representatives.scenario)
        if value is not None
    ]
    require(
        all(value.representative.rerun_snapshot_matches for value in representatives),
        "representative rerun snapshot differs",
    )
    checks += 1
    require(
        result.execution.ordinary_run_included_event_count == 0
        and result.execution.ordinary_run_retained_event_count == 0,
        "ordinary events were retained",
    )
    checks += 1
    require(
        result.execution.representative_reruns <= 2
        and result.execution.maximum_simultaneously_retained_event_rich_results <= 2,
        "representative retention exceeded two",
    )
    checks += 1
    require(
        result.work_budget.estimated_work_units
        == result.work_budget.baseline_item_count
        * result.work_budget.run_count
        * result.work_budget.model_variants,
        "work budget calculation differs",
    )
    checks += 1
    require(
        all(
            scenario.applied_override_count == len(scenario.applied_overrides)
            for scenario in result.scenarios
        ),
        "applied override evidence differs",
    )
    checks += 1
    require(
        all(
            scenario.scenario_model_hash is not None
            for scenario in result.scenarios
            if scenario.status == "valid"
        ),
        "valid scenario hash is missing",
    )
    checks += 1
    return checks
