import argparse
import json
import platform
import time
from collections.abc import Sequence
from typing import Any

from app.benchmark import performance_model
from app.domain.comparison import ScenarioComparisonRequest
from app.domain.models import SimulationResult
from app.engine.simulator import run_simulation
from app.scenarios.coordinator import run_scenario_comparison

BASE_SEED = 20250715


def _scenarios(count: int) -> list[dict[str, object]]:
    definitions = [
        ("capacity-2", "resourcePool", "server", "capacity", 2),
        ("service-040", "stage", "service", "processing.fixed.value", 0.4),
        ("arrival-120", "source", "jobs", "arrivalInterval", 1.2),
        ("sla-9", "slaRule", "default", "targetDuration", 9),
        ("service-030", "stage", "service", "processing.fixed.value", 0.3),
    ]
    return [
        {
            "id": scenario_id,
            "name": scenario_id,
            "overrides": [
                {
                    "entityType": entity_type,
                    "entityId": entity_id,
                    "field": field,
                    "operation": "replace",
                    "value": value,
                }
            ],
        }
        for scenario_id, entity_type, entity_id, field, value in definitions[:count]
    ]


def benchmark_case(
    item_count: int,
    run_count: int,
    scenario_count: int,
    sample_limit: int = 25,
) -> dict[str, Any]:
    simulation_durations: list[float] = []

    def timed_runner(*args: object, **kwargs: object) -> SimulationResult:
        started = time.perf_counter()
        result = run_simulation(*args, **kwargs)  # type: ignore[arg-type]
        simulation_durations.append(time.perf_counter() - started)
        return result

    request = ScenarioComparisonRequest.model_validate(
        {
            "baselineModel": performance_model(item_count),
            "scenarios": _scenarios(scenario_count),
            "execution": {"baseSeed": BASE_SEED, "runCount": run_count},
            "objective": {"metric": "averageCycleTime", "direction": "minimize"},
            "representativeEvidence": {
                "detailMode": "sampled",
                "sampledItemLimit": sample_limit,
            },
        }
    )
    started = time.perf_counter()
    result = run_scenario_comparison(request, simulation_runner=timed_runner)
    execution_seconds = time.perf_counter() - started
    baseline_representative = result.representatives.baseline
    scenario_representative = result.representatives.scenario
    return {
        "model": request.baseline_model.name,
        "baseSeed": BASE_SEED,
        "itemsPerRun": item_count,
        "runCount": run_count,
        "scenarioCount": scenario_count,
        "totalModelVariants": result.work_budget.model_variants,
        "estimatedWorkUnits": result.work_budget.estimated_work_units,
        "ordinarySimulationExecutions": result.execution.ordinary_simulation_executions,
        "representativeReruns": result.execution.representative_reruns,
        "executionSeconds": execution_seconds,
        "meanSimulationExecutionSeconds": (
            sum(simulation_durations) / len(simulation_durations)
        ),
        "totalGeneratedEventCount": result.execution.total_generated_event_count,
        "aggregateComparisonPayloadBytes": len(
            result.model_dump_json(by_alias=True).encode("utf-8")
        ),
        "baselineRepresentativePayloadBytes": (
            len(
                baseline_representative.representative.result.model_dump_json(
                    by_alias=True
                ).encode("utf-8")
            )
            if baseline_representative is not None
            else 0
        ),
        "scenarioRepresentativePayloadBytes": (
            len(
                scenario_representative.representative.result.model_dump_json(
                    by_alias=True
                ).encode("utf-8")
            )
            if scenario_representative is not None
            else 0
        ),
        "successfulScenarios": sum(
            scenario.status == "valid" for scenario in result.scenarios
        ),
        "failedScenarios": sum(
            scenario.status == "failed" for scenario in result.scenarios
        ),
        "minimumPairedRunRatioObserved": min(
            scenario.paired_run_ratio for scenario in result.scenarios
        ),
        "maximumSimultaneouslyRetainedEventRichResults": (
            result.execution.maximum_simultaneously_retained_event_rich_results
        ),
        "returnedEventCount": result.execution.returned_event_count,
        "integrity": result.integrity.status,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark OpsTwin scenario comparison")
    parser.add_argument("--smoke", action="store_true")
    arguments = parser.parse_args(argv)
    cases = [(10, 2, 1, 2)] if arguments.smoke else [
        (100, 10, 2, 25),
        (100, 100, 2, 25),
        (1_000, 10, 2, 25),
        (100, 50, 5, 25),
    ]
    output = {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "results": [benchmark_case(*case) for case in cases],
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
