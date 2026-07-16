import argparse
import json
import platform
import time
from collections.abc import Sequence
from typing import Any

from app.benchmark import performance_model
from app.domain.sensitivity import SensitivityRequest
from app.sensitivity.coordinator import run_sensitivity_analysis

BASE_SEED = 20260716


def benchmark_case(item_count: int, run_count: int, value_count: int) -> dict[str, Any]:
    request = SensitivityRequest.model_validate(
        {
            "baselineModel": performance_model(item_count),
            "target": {"entityType": "resourcePool", "entityId": "server", "field": "capacity"},
            "values": list(range(1, value_count + 1)),
            "execution": {"baseSeed": BASE_SEED, "runCount": run_count},
            "metrics": ["averageCycleTime", "slaAttainment", "timeWeightedQueueLength"],
        }
    )
    started = time.perf_counter()
    result = run_sensitivity_analysis(request)
    execution_seconds = time.perf_counter() - started
    return {
        "itemsPerRun": item_count,
        "runCount": run_count,
        "valueCount": value_count,
        "estimatedWorkUnits": result.work_budget.estimated_work_units,
        "ordinarySimulationExecutions": result.execution.ordinary_simulation_executions,
        "minimumPairedRunRatioObserved": min(value.paired_run_ratio for value in result.values),
        "executionSeconds": execution_seconds,
        "payloadBytes": len(result.model_dump_json(by_alias=True).encode("utf-8")),
        "returnedEventCount": result.execution.ordinary_run_retained_event_count,
        "integrityChecks": result.integrity.checks_run,
        "integrity": result.integrity.status,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark OpsTwin sensitivity analysis")
    parser.add_argument("--smoke", action="store_true")
    arguments = parser.parse_args(argv)
    cases = (
        [(10, 2, 2)]
        if arguments.smoke
        else [
            (100, 10, 3),
            (100, 50, 5),
            (100, 100, 5),
            (1000, 10, 3),
        ]
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
