from copy import deepcopy
from typing import Any

import pytest

import app.scenarios.coordinator as coordinator_module
from app.domain.comparison import ScenarioComparisonRequest
from app.domain.models import ResultDetailConfig, SimulationResult
from app.engine.seed_schedule import seed_schedule
from app.engine.simulator import run_simulation
from app.scenarios.coordinator import (
    ComparisonWorkBudgetError,
    ScenarioComparisonError,
    run_scenario_comparison,
)
from app.scenarios.integrity import (
    ComparisonIntegrityError,
    validate_comparison_integrity,
)


def comparison_request(
    support_model_data: dict[str, Any],
    *,
    run_count: int = 3,
    scenarios: list[dict[str, object]] | None = None,
    minimum_paired_ratio: float = 1.0,
    representative_detail: str = "summary",
) -> ScenarioComparisonRequest:
    scenario_values = scenarios or [
        {
            "id": "more-support",
            "name": "More support",
            "overrides": [
                {
                    "entityType": "resourcePool",
                    "entityId": "support",
                    "field": "capacity",
                    "operation": "replace",
                    "value": 3,
                }
            ],
        }
    ]
    return ScenarioComparisonRequest.model_validate(
        {
            "schemaVersion": "0.5.0",
            "baselineModel": support_model_data,
            "scenarios": scenario_values,
            "execution": {
                "baseSeed": 42,
                "runCount": run_count,
                "minimumSuccessfulRunRatio": 0.5,
                "minimumPairedRunRatio": minimum_paired_ratio,
                "thresholds": {"maximumAverageCycleTime": 12},
            },
            "objective": {"metric": "averageCycleTime", "direction": "minimize"},
            "guardrails": [
                {
                    "metric": "terminalFailureRate",
                    "operator": "lessThanOrEqual",
                    "value": 0.5,
                }
            ],
            "representativeEvidence": {
                "baseline": True,
                "topRankedScenario": True,
                "detailMode": representative_detail,
                "sampledItemLimit": 2 if representative_detail == "sampled" else None,
            },
        }
    )


def test_gm033_paired_execution_uses_shared_seeds_and_summary_evidence(
    support_model_data: dict[str, Any],
) -> None:
    calls: list[tuple[int, int, str]] = []

    def recording_runner(*args: object, **kwargs: object) -> SimulationResult:
        model = args[0]
        support_capacity = next(
            pool.capacity for pool in model.resource_pools if pool.id == "support"
        )
        detail = kwargs["result_detail"]
        assert isinstance(detail, ResultDetailConfig)
        calls.append((support_capacity, int(kwargs["seed_override"]), detail.mode))
        return run_simulation(*args, **kwargs)  # type: ignore[arg-type]

    result = run_scenario_comparison(
        comparison_request(support_model_data), simulation_runner=recording_runner
    )
    seeds = seed_schedule(42, 3)

    assert calls[:6] == [
        (capacity, seed, "summary")
        for seed in seeds
        for capacity in (2, 3)
    ]
    assert result.execution.ordinary_simulation_executions == 6
    assert result.execution.ordinary_run_included_event_count == 0
    assert result.execution.ordinary_run_retained_event_count == 0
    assert result.scenarios[0].paired_run_indexes == [0, 1, 2]
    assert result.scenarios[0].paired_run_ratio == 1
    utilization = result.scenarios[0].resource_utilization_deltas["support"]
    assert utilization.absolute_delta.count == 3


def test_gm037_comparison_is_reproducible_and_baseline_is_immutable(
    support_model_data: dict[str, Any],
) -> None:
    before = deepcopy(support_model_data)
    request = comparison_request(support_model_data)

    first = run_scenario_comparison(request)
    second = run_scenario_comparison(request)

    assert first == second
    assert support_model_data == before
    assert first.baseline.model_hash == second.baseline.model_hash
    assert first.ranking == second.ranking


def test_scenario_input_order_does_not_change_per_scenario_evidence_or_ranking(
    support_model_data: dict[str, Any],
) -> None:
    scenarios = [
        {
            "id": f"capacity-{capacity}",
            "name": f"Capacity {capacity}",
            "overrides": [
                {
                    "entityType": "resourcePool",
                    "entityId": "support",
                    "field": "capacity",
                    "value": capacity,
                }
            ],
        }
        for capacity in (3, 4)
    ]

    forward = run_scenario_comparison(
        comparison_request(support_model_data, scenarios=scenarios)
    )
    reversed_result = run_scenario_comparison(
        comparison_request(support_model_data, scenarios=list(reversed(scenarios)))
    )

    forward_by_id = {row.scenario_id: row for row in forward.scenarios}
    reversed_by_id = {row.scenario_id: row for row in reversed_result.scenarios}
    assert forward_by_id == reversed_by_id
    assert forward.ranking == reversed_result.ranking


def test_gm039_invalid_scenario_is_isolated_from_valid_scenario(
    support_model_data: dict[str, Any],
) -> None:
    invalid = {
        "id": "invalid",
        "name": "Invalid",
        "overrides": [
            {
                "entityType": "resourcePool",
                "entityId": "missing",
                "field": "capacity",
                "operation": "replace",
                "value": 3,
            }
        ],
    }
    valid = {
        "id": "valid",
        "name": "Valid",
        "overrides": [
            {
                "entityType": "resourcePool",
                "entityId": "support",
                "field": "capacity",
                "operation": "replace",
                "value": 3,
            }
        ],
    }

    result = run_scenario_comparison(
        comparison_request(support_model_data, scenarios=[invalid, valid])
    )

    failed = next(scenario for scenario in result.scenarios if scenario.scenario_id == "invalid")
    succeeded = next(scenario for scenario in result.scenarios if scenario.scenario_id == "valid")
    assert failed.status == "failed"
    assert failed.failure is not None
    assert failed.failure.category == "override_validation"
    assert succeeded.status == "valid"
    assert [row.scenario_id for row in result.ranking] == ["valid"]


def test_scenario_below_paired_ratio_is_visible_and_unranked(
    support_model_data: dict[str, Any],
) -> None:
    failed_seed = seed_schedule(42, 3)[1]

    def one_scenario_failure(*args: object, **kwargs: object) -> SimulationResult:
        model = args[0]
        support_capacity = next(
            pool.capacity for pool in model.resource_pools if pool.id == "support"
        )
        if support_capacity == 3 and kwargs["seed_override"] == failed_seed:
            raise RuntimeError("private")
        return run_simulation(*args, **kwargs)  # type: ignore[arg-type]

    result = run_scenario_comparison(
        comparison_request(support_model_data, minimum_paired_ratio=1.0),
        simulation_runner=one_scenario_failure,
    )

    scenario = result.scenarios[0]
    assert scenario.status == "failed"
    assert scenario.failure is not None
    assert scenario.failure.category == "paired_ratio_failure"
    assert scenario.paired_run_count == 2
    assert scenario.paired_run_ratio == pytest.approx(2 / 3)
    assert result.ranking == []


def test_all_scenario_run_failures_do_not_invalidate_baseline(
    support_model_data: dict[str, Any],
) -> None:
    def scenario_failure(*args: object, **kwargs: object) -> SimulationResult:
        model = args[0]
        support_capacity = next(
            pool.capacity for pool in model.resource_pools if pool.id == "support"
        )
        if support_capacity == 3:
            raise RuntimeError("private")
        return run_simulation(*args, **kwargs)  # type: ignore[arg-type]

    result = run_scenario_comparison(
        comparison_request(support_model_data), simulation_runner=scenario_failure
    )

    assert result.baseline.successful_run_count == 3
    assert result.scenarios[0].status == "failed"
    assert result.scenarios[0].failure is not None
    assert result.scenarios[0].failure.category == "paired_execution"
    assert result.scenarios[0].variant is None
    assert result.ranking == []


def test_baseline_execution_failure_invalidates_comparison(
    support_model_data: dict[str, Any],
) -> None:
    def failure(*args: object, **kwargs: object) -> SimulationResult:
        raise RuntimeError("private")

    with pytest.raises(ScenarioComparisonError, match="Baseline comparison"):
        run_scenario_comparison(
            comparison_request(support_model_data), simulation_runner=failure
        )


def test_representatives_are_bounded_and_match_original_snapshots(
    support_model_data: dict[str, Any],
) -> None:
    result = run_scenario_comparison(
        comparison_request(support_model_data, representative_detail="sampled")
    )

    assert result.representatives.baseline is not None
    assert result.representatives.scenario is not None
    assert result.representatives.baseline.representative.rerun_snapshot_matches is True
    assert result.representatives.scenario.representative.rerun_snapshot_matches is True
    assert result.representatives.baseline.representative.included_event_count > 0
    assert result.execution.representative_reruns == 2
    assert result.execution.maximum_simultaneously_retained_event_rich_results == 2


def test_gm040_comparison_integrity_reports_real_checks(
    support_model_data: dict[str, Any],
) -> None:
    result = run_scenario_comparison(comparison_request(support_model_data))

    assert result.integrity.status == "passed"
    assert result.integrity.checks_run >= 15


def test_gm040_integrity_rejects_malformed_retention_and_pair_count(
    support_model_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def capture(*args: object, **kwargs: object) -> int:
        captured["args"] = args
        return validate_comparison_integrity(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(coordinator_module, "validate_comparison_integrity", capture)
    result = run_scenario_comparison(comparison_request(support_model_data))
    args = captured["args"]
    assert isinstance(args, tuple)
    request, _, baseline_snapshots, scenario_snapshots = args

    bad_execution = result.execution.model_copy(
        update={"ordinary_run_retained_event_count": 1}
    )
    with pytest.raises(ComparisonIntegrityError, match="ordinary events"):
        validate_comparison_integrity(
            request,
            result.model_copy(update={"execution": bad_execution}),
            baseline_snapshots,
            scenario_snapshots,
        )

    scenario = result.scenarios[0]
    bad_scenario = scenario.model_copy(
        update={"paired_run_count": scenario.paired_run_count + 1}
    )
    with pytest.raises(ComparisonIntegrityError, match="intersection"):
        validate_comparison_integrity(
            request,
            result.model_copy(update={"scenarios": [bad_scenario]}),
            baseline_snapshots,
            scenario_snapshots,
        )


def test_work_budget_rejects_before_simulation(
    support_model_data: dict[str, Any],
) -> None:
    support_model_data["sources"][0]["itemCount"] = 1000
    scenarios = [
        {
            "id": f"scenario-{index}",
            "name": f"Scenario {index}",
            "overrides": [
                {
                    "entityType": "resourcePool",
                    "entityId": "support",
                    "field": "capacity",
                    "operation": "replace",
                    "value": index + 3,
                }
            ],
        }
        for index in range(5)
    ]
    request = comparison_request(
        support_model_data, run_count=500, scenarios=scenarios
    )

    with pytest.raises(ComparisonWorkBudgetError) as captured:
        run_scenario_comparison(request)

    assert captured.value.estimated_work_units == 3_000_000
    assert captured.value.maximum_work_units == 100_000
