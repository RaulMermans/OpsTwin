import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from app.domain.comparison import ScenarioComparisonRequest
from app.domain.economics import EconomicComparisonRequest, EconomicSensitivityRequest
from app.domain.models import ObservationConfig, OperationalModel, ResultDetailConfig
from app.domain.repeated import (
    RepeatedSimulationRequest,
    RepresentativeRunConfig,
    RiskThresholds,
)
from app.domain.sensitivity import SensitivityRequest
from app.economics.comparison import run_economic_comparison
from app.economics.sensitivity import run_economic_sensitivity
from app.engine.integrity import SimulationIntegrityError
from app.engine.repeated import RepeatedSimulationError, run_repeated_simulation
from app.engine.simulator import run_simulation
from app.scenarios.coordinator import ScenarioComparisonError, run_scenario_comparison
from app.sensitivity.coordinator import SensitivityAnalysisError, run_sensitivity_analysis
from app.sensitivity.materializer import SensitivityPreparationError


def load_model(path: Path) -> OperationalModel:
    """Load and validate an operational model from JSON."""
    with path.open(encoding="utf-8") as model_file:
        data: Any = json.load(model_file)
    return OperationalModel.model_validate(data)


def run_model(
    path: Path,
    seed_override: int | None = None,
    observation: ObservationConfig | None = None,
    result_detail: ResultDetailConfig | None = None,
) -> dict[str, Any]:
    """Run a model and serialize the shared typed simulation result."""
    result = run_simulation(
        load_model(path),
        seed_override=seed_override,
        observation=observation or ObservationConfig(),
        result_detail=result_detail or ResultDetailConfig(mode="summary"),
    )
    return result.model_dump(mode="json", by_alias=True)


def run_repeated_model(
    path: Path,
    base_seed: int,
    run_count: int = 100,
    confidence_level: float = 0.95,
    minimum_successful_run_ratio: float = 1.0,
    observation: ObservationConfig | None = None,
    thresholds: RiskThresholds | None = None,
    representative_detail: Literal["summary", "sampled", "full"] = "sampled",
    sampled_item_limit: int | None = None,
) -> dict[str, Any]:
    """Run a repeated request and serialize its typed aggregate result."""
    effective_limit = sampled_item_limit
    if representative_detail == "sampled" and effective_limit is None:
        effective_limit = 25
    request = RepeatedSimulationRequest(
        model=load_model(path),
        base_seed=base_seed,
        run_count=run_count,
        confidence_level=confidence_level,
        minimum_successful_run_ratio=minimum_successful_run_ratio,
        observation=observation or ObservationConfig(),
        thresholds=thresholds or RiskThresholds(),
        representative_run=RepresentativeRunConfig(
            detail_mode=representative_detail,
            sampled_item_limit=effective_limit,
        ),
    )
    return run_repeated_simulation(request).model_dump(mode="json", by_alias=True)


def run_comparison_request(
    path: Path,
    *,
    base_seed: int | None = None,
    run_count: int | None = None,
    confidence_level: float | None = None,
    minimum_successful_run_ratio: float | None = None,
    minimum_paired_run_ratio: float | None = None,
    representative_detail: Literal["summary", "sampled", "full"] | None = None,
    sampled_item_limit: int | None = None,
) -> dict[str, Any]:
    """Load, optionally override, execute, and serialize one comparison request."""
    with path.open(encoding="utf-8") as request_file:
        data: Any = json.load(request_file)
    request = ScenarioComparisonRequest.model_validate(data)
    execution_updates = {
        key: value
        for key, value in {
            "base_seed": base_seed,
            "run_count": run_count,
            "confidence_level": confidence_level,
            "minimum_successful_run_ratio": minimum_successful_run_ratio,
            "minimum_paired_run_ratio": minimum_paired_run_ratio,
        }.items()
        if value is not None
    }
    representative_updates: dict[str, object] = {}
    if representative_detail is not None:
        representative_updates["detail_mode"] = representative_detail
        representative_updates["sampled_item_limit"] = (
            sampled_item_limit if representative_detail == "sampled" else None
        )
    elif sampled_item_limit is not None:
        representative_updates["sampled_item_limit"] = sampled_item_limit
    request = request.model_copy(
        update={
            "execution": request.execution.model_copy(update=execution_updates),
            "representative_evidence": request.representative_evidence.model_copy(
                update=representative_updates
            ),
        }
    )
    request = ScenarioComparisonRequest.model_validate(
        request.model_dump(mode="json", by_alias=True)
    )
    return run_scenario_comparison(request).model_dump(mode="json", by_alias=True)


def run_sensitivity_request(path: Path) -> dict[str, Any]:
    """Load, validate, execute, and serialize one sensitivity request."""
    with path.open(encoding="utf-8") as request_file:
        data: Any = json.load(request_file)
    request = SensitivityRequest.model_validate(data)
    return run_sensitivity_analysis(request).model_dump(mode="json", by_alias=True)


def run_economic_request(path: Path) -> dict[str, Any]:
    """Load, validate, execute, and serialize one economic comparison request."""
    with path.open(encoding="utf-8") as request_file:
        data: Any = json.load(request_file)
    request = EconomicComparisonRequest.model_validate(data)
    return run_economic_comparison(request).model_dump(mode="json", by_alias=True)


def run_economic_sensitivity_request(path: Path) -> dict[str, Any]:
    """Load, validate, execute, and serialize one economic sensitivity request."""
    with path.open(encoding="utf-8") as request_file:
        data: Any = json.load(request_file)
    request = EconomicSensitivityRequest.model_validate(data)
    return run_economic_sensitivity(request).model_dump(mode="json", by_alias=True)


def _single_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an OpsTwin seeded model")
    parser.add_argument("model", type=Path)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--result-detail", choices=("summary", "sampled", "full"), default="summary"
    )
    parser.add_argument("--sampled-item-limit", type=int, default=None)
    parser.add_argument("--warmup-duration", type=float, default=0)
    parser.add_argument("--measurement-duration", type=float, default=None)
    return parser


def _repeated_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OpsTwin repeated simulation")
    parser.add_argument("model", type=Path)
    parser.add_argument("--base-seed", type=int, required=True)
    parser.add_argument("--run-count", type=int, default=100)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--minimum-successful-run-ratio", type=float, default=1.0)
    parser.add_argument("--warmup-duration", type=float, default=0)
    parser.add_argument("--measurement-duration", type=float, default=None)
    parser.add_argument("--minimum-sla-attainment", type=float, default=None)
    parser.add_argument("--maximum-average-cycle-time", type=float, default=None)
    parser.add_argument("--maximum-p95-cycle-time", type=float, default=None)
    parser.add_argument("--maximum-time-weighted-queue-length", type=float, default=None)
    parser.add_argument("--maximum-terminal-failure-rate", type=float, default=None)
    parser.add_argument(
        "--representative-detail",
        choices=("summary", "sampled", "full"),
        default="sampled",
    )
    parser.add_argument("--sampled-item-limit", type=int, default=None)
    return parser


def _comparison_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare OpsTwin scenarios")
    parser.add_argument("request", type=Path)
    parser.add_argument("--base-seed", type=int, default=None)
    parser.add_argument("--run-count", type=int, default=None)
    parser.add_argument("--confidence-level", type=float, default=None)
    parser.add_argument("--minimum-successful-run-ratio", type=float, default=None)
    parser.add_argument("--minimum-paired-run-ratio", type=float, default=None)
    parser.add_argument(
        "--representative-detail",
        choices=("summary", "sampled", "full"),
        default=None,
    )
    parser.add_argument("--sampled-item-limit", type=int, default=None)
    return parser


def _sensitivity_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OpsTwin sensitivity analysis")
    parser.add_argument("request", type=Path)
    return parser


def _economic_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("request", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Parse CLI arguments and print exactly one JSON payload."""
    arguments_list = list(argv) if argv is not None else sys.argv[1:]
    command = arguments_list[0] if arguments_list else None
    repeated = command == "repeated"
    comparison = command == "compare"
    sensitivity = command == "sensitivity"
    economics = command == "economics"
    economic_sensitivity = command == "economic-sensitivity"
    parser = (
        _repeated_parser()
        if repeated
        else _comparison_parser()
        if comparison
        else _sensitivity_parser()
        if sensitivity
        else _economic_parser("Run OpsTwin economic comparison")
        if economics
        else _economic_parser("Run OpsTwin economic sensitivity")
        if economic_sensitivity
        else _single_parser()
    )
    arguments = parser.parse_args(
        arguments_list[1:]
        if repeated or comparison or sensitivity or economics or economic_sensitivity
        else arguments_list
    )
    try:
        if economic_sensitivity:
            print(
                json.dumps(
                    run_economic_sensitivity_request(arguments.request),
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        if economics:
            print(json.dumps(run_economic_request(arguments.request), indent=2, sort_keys=True))
            return
        if sensitivity:
            print(json.dumps(run_sensitivity_request(arguments.request), indent=2, sort_keys=True))
            return
        if comparison:
            payload = run_comparison_request(
                arguments.request,
                base_seed=arguments.base_seed,
                run_count=arguments.run_count,
                confidence_level=arguments.confidence_level,
                minimum_successful_run_ratio=(arguments.minimum_successful_run_ratio),
                minimum_paired_run_ratio=arguments.minimum_paired_run_ratio,
                representative_detail=arguments.representative_detail,
                sampled_item_limit=arguments.sampled_item_limit,
            )
            print(json.dumps(payload, indent=2, sort_keys=True))
            return
        observation = ObservationConfig(
            warmup_duration=arguments.warmup_duration,
            measurement_duration=arguments.measurement_duration,
        )
        if repeated:
            thresholds = RiskThresholds(
                minimum_sla_attainment=arguments.minimum_sla_attainment,
                maximum_average_cycle_time=arguments.maximum_average_cycle_time,
                maximum_p95_cycle_time=arguments.maximum_p95_cycle_time,
                maximum_time_weighted_queue_length=(arguments.maximum_time_weighted_queue_length),
                maximum_terminal_failure_rate=arguments.maximum_terminal_failure_rate,
            )
            payload = run_repeated_model(
                arguments.model,
                arguments.base_seed,
                arguments.run_count,
                arguments.confidence_level,
                arguments.minimum_successful_run_ratio,
                observation,
                thresholds,
                arguments.representative_detail,
                arguments.sampled_item_limit,
            )
        else:
            result_detail = ResultDetailConfig(
                mode=arguments.result_detail,
                sampled_item_limit=arguments.sampled_item_limit,
            )
            payload = run_model(
                arguments.model,
                arguments.seed,
                observation,
                result_detail,
            )
    except ValidationError as error:
        parser.error(str(error))
    except SimulationIntegrityError:
        parser.exit(2, "Simulation integrity validation failed\n")
    except RepeatedSimulationError:
        parser.exit(2, "Repeated simulation failed its success policy\n")
    except ScenarioComparisonError:
        parser.exit(2, "Scenario comparison failed\n")
    except (SensitivityPreparationError, SensitivityAnalysisError):
        parser.exit(2, "Sensitivity analysis failed\n")
    except ValueError:
        parser.exit(2, "Economic analysis failed\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
