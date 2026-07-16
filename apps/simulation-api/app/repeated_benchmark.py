import argparse
import json
import platform
import time
from collections.abc import Sequence
from typing import Any

from app.benchmark import performance_model
from app.domain.models import ResultDetailConfig, SimulationResult
from app.domain.repeated import RepeatedSimulationRequest, RepresentativeRunConfig
from app.engine.repeated import run_repeated_simulation
from app.engine.simulator import run_simulation

BASE_SEED = 20250715


def benchmark_case(
    item_count: int, run_count: int, sampled_item_limit: int = 25
) -> dict[str, Any]:
    ordinary_durations: list[float] = []

    def timed_runner(*args: object, **kwargs: object) -> SimulationResult:
        started = time.perf_counter()
        result = run_simulation(*args, **kwargs)  # type: ignore[arg-type]
        detail = kwargs.get("result_detail")
        if isinstance(detail, ResultDetailConfig) and detail.mode == "summary":
            ordinary_durations.append(time.perf_counter() - started)
        return result

    request = RepeatedSimulationRequest(
        model=performance_model(item_count),
        base_seed=BASE_SEED,
        run_count=run_count,
        representative_run=RepresentativeRunConfig(
            detail_mode="sampled",
            sampled_item_limit=sampled_item_limit,
        ),
    )
    started = time.perf_counter()
    result = run_repeated_simulation(request, simulation_runner=timed_runner)
    execution_seconds = time.perf_counter() - started
    payload = result.model_dump_json(by_alias=True).encode()
    representative_payload = result.representative_run.result.model_dump_json(
        by_alias=True
    ).encode()
    return {
        "model": request.model.name,
        "baseSeed": BASE_SEED,
        "runCount": run_count,
        "itemsPerRun": item_count,
        "stageCount": len(request.model.stages),
        "ordinaryRunCount": result.execution.ordinary_run_count,
        "representativeRerunCount": result.execution.representative_rerun_count,
        "executionSeconds": execution_seconds,
        "meanOrdinaryRunSeconds": sum(ordinary_durations) / len(ordinary_durations),
        "aggregatePayloadBytes": len(payload),
        "representativePayloadBytes": len(representative_payload),
        "successfulRuns": result.successful_run_count,
        "failedRuns": result.failed_run_count,
        "maximumSimultaneouslyRetainedFullResults": (
            result.execution.maximum_simultaneously_retained_single_run_results
        ),
        "totalGeneratedEventCount": result.execution.total_generated_event_count,
        "returnedEventCount": result.execution.returned_event_count,
        "integrity": result.integrity.status,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark repeated OpsTwin simulation")
    parser.add_argument("--smoke", action="store_true")
    arguments = parser.parse_args(argv)
    cases = [(10, 2, 2)] if arguments.smoke else [
        (100, 10, 25),
        (100, 100, 25),
        (1_000, 10, 25),
        (1_000, 50, 25),
    ]
    output = {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "results": [
            benchmark_case(item_count, run_count, limit)
            for item_count, run_count, limit in cases
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
