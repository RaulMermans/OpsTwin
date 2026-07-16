import argparse
import json
import platform
from collections.abc import Sequence
from time import perf_counter
from typing import Literal

from app.domain.models import OperationalModel, ResultDetailConfig
from app.engine.simulator import run_simulation

DetailMode = Literal["summary", "sampled", "full"]


def performance_model(item_count: int) -> OperationalModel:
    """Build the bounded deterministic model used only for local baselines."""
    return OperationalModel.model_validate(
        {
            "schemaVersion": "0.2.0",
            "name": "Performance baseline",
            "timeUnit": "minutes",
            "runConfig": {"seed": 20250715},
            "sources": [
                {
                    "id": "jobs",
                    "name": "Jobs",
                    "itemCount": item_count,
                    "initialArrivalTime": 0,
                    "priority": 0,
                    "firstStageId": "service",
                    "arrival": {"type": "fixed", "interval": 1},
                }
            ],
            "resourcePools": [{"id": "server", "name": "Server", "capacity": 1}],
            "stages": [
                {
                    "id": "service",
                    "name": "Service",
                    "resourcePoolId": "server",
                    "processingTime": {"type": "fixed", "value": 0.5},
                    "queuePolicy": "fifo",
                }
            ],
            "routes": [
                {
                    "id": "complete",
                    "kind": "success",
                    "fromStageId": "service",
                    "options": [{"targetType": "completion", "probability": 1}],
                }
            ],
            "slaRules": [{"id": "default", "targetDuration": 10}],
        }
    )


def benchmark_case(
    item_count: int,
    mode: DetailMode,
    sampled_item_limit: int | None = None,
) -> dict[str, object]:
    """Measure one run and its selected JSON payload on the current machine."""
    detail = ResultDetailConfig(mode=mode, sampled_item_limit=sampled_item_limit)
    started = perf_counter()
    result = run_simulation(performance_model(item_count), result_detail=detail)
    execution_seconds = perf_counter() - started
    serialization_started = perf_counter()
    payload = result.model_dump_json(by_alias=True)
    serialization_seconds = perf_counter() - serialization_started
    return {
        "model": result.run.model_name,
        "seed": result.run.seed,
        "resultDetailMode": mode,
        "itemCount": item_count,
        "stageCount": len(result.stage_metrics),
        "eventCount": result.result_detail.total_event_count,
        "includedEventCount": result.result_detail.included_event_count,
        "executionSeconds": execution_seconds,
        "serializationSeconds": serialization_seconds,
        "payloadBytes": len(payload.encode("utf-8")),
        "integrity": result.integrity.status,
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Run the smoke or full local simulation performance baseline."""
    parser = argparse.ArgumentParser(description="Benchmark OpsTwin simulation payload modes")
    parser.add_argument("--smoke", action="store_true")
    arguments = parser.parse_args(argv)
    cases: list[tuple[int, DetailMode, int | None]]
    if arguments.smoke:
        cases = [(100, "summary", None)]
    else:
        cases = [
            (100, "summary", None),
            (100, "full", None),
            (1_000, "summary", None),
            (1_000, "full", None),
            (10_000, "summary", None),
            (10_000, "full", None),
            (10_000, "sampled", 25),
        ]
    output = {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "results": [
            benchmark_case(item_count, mode, limit) for item_count, mode, limit in cases
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
