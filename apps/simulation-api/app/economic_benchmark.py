from __future__ import annotations

import argparse
import json
import platform
import time
from collections.abc import Sequence
from typing import Any

from app.benchmark import performance_model
from app.domain.economics import EconomicComparisonRequest
from app.economics.comparison import run_economic_comparison

BASE_SEED = 20260716


def benchmark_case(item_count: int, run_count: int, scenario_count: int) -> dict[str, Any]:
    scenarios = [
        {
            "id": f"capacity-{capacity}",
            "name": f"Capacity {capacity}",
            "overrides": [
                {
                    "entityType": "resourcePool",
                    "entityId": "server",
                    "field": "capacity",
                    "value": capacity,
                }
            ],
        }
        for capacity in range(2, 2 + scenario_count)
    ]
    request = EconomicComparisonRequest.model_validate(
        {
            "comparison": {
                "baselineModel": performance_model(item_count),
                "scenarios": scenarios,
                "execution": {"baseSeed": BASE_SEED, "runCount": run_count},
                "objective": {"metric": "averageCycleTime", "direction": "minimize"},
                "representativeEvidence": {
                    "baseline": False,
                    "topRankedScenario": False,
                    "detailMode": "summary",
                    "sampledItemLimit": None,
                },
            },
            "assumptions": {
                "currency": "EUR",
                "modelTimeUnit": "minutes",
                "resourceProvisioning": [
                    {"resourcePoolId": "server", "costPerCapacityTimeUnit": 2}
                ],
                "queueHolding": [{"costPerItemTimeUnit": 0.5}],
            },
        }
    )
    started = time.perf_counter()
    result = run_economic_comparison(request, record_evaluation_timing=True)
    total = time.perf_counter() - started
    return {
        "itemsPerRun": item_count,
        "runCount": run_count,
        "scenarioCount": scenario_count,
        "variantCount": scenario_count + 1,
        "estimatedWorkUnits": result.work_budget.estimated_work_units,
        "simulationSeconds": max(0, total - result.execution.economic_evaluation_seconds),
        "economicEvaluationSeconds": result.execution.economic_evaluation_seconds,
        "totalSeconds": total,
        "responseBytes": len(result.model_dump_json(by_alias=True).encode("utf-8")),
        "minimumPairedRunRatio": min(item.paired_run_ratio for item in result.scenarios),
        "costSnapshotCount": result.execution.economic_snapshot_evaluations,
        "undefinedCostPerCompletionCount": sum(
            item.scenario_cost.undefined_cost_per_completed_item_count
            for item in result.scenarios
            if item.scenario_cost is not None
        ),
        "retainedEvents": result.execution.ordinary_run_retained_event_count,
        "integrityChecks": result.integrity.checks_run,
        "integrity": result.integrity.status,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark OpsTwin economic comparison")
    parser.add_argument("--smoke", action="store_true")
    arguments = parser.parse_args(argv)
    cases = (
        [(10, 2, 1)]
        if arguments.smoke
        else [(100, 10, 1), (100, 50, 2), (100, 100, 2), (1000, 10, 2)]
    )
    print(
        json.dumps(
            {
                "environment": {
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                },
                "results": [benchmark_case(*case) for case in cases],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
