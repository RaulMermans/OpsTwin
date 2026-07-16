import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.cli import load_model, run_model
from app.domain.comparison import ScenarioComparisonRequest
from app.domain.repeated import RepeatedSimulationRequest
from app.engine.repeated import run_repeated_simulation
from app.engine.simulator import run_simulation
from app.scenarios.coordinator import run_scenario_comparison


def test_all_examples_validate_against_operational_model_schema(repository_root: Path) -> None:
    schema_path = repository_root / "contracts" / "operational-model.schema.json"
    with schema_path.open(encoding="utf-8") as schema_file:
        schema: dict[str, Any] = json.load(schema_file)

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    example_paths = [
        repository_root / "examples" / "support-baseline.json",
        repository_root / "examples" / "support-deterministic.json",
    ]
    for example_path in example_paths:
        with example_path.open(encoding="utf-8") as example_file:
            validator.validate(json.load(example_file))


def test_comparison_example_validates_as_typed_request(repository_root: Path) -> None:
    example = json.loads(
        (repository_root / "examples" / "support-comparison.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (
            repository_root
            / "contracts"
            / "scenario-comparison-request.schema.json"
        ).read_text(encoding="utf-8")
    )
    operational_schema = json.loads(
        (repository_root / "contracts" / "operational-model.schema.json").read_text(
            encoding="utf-8"
        )
    )
    registry = Registry().with_resource(
        operational_schema["$id"], Resource.from_contents(operational_schema)
    )

    request = ScenarioComparisonRequest.model_validate(example)

    Draft202012Validator(schema, registry=registry).validate(example)
    assert request.scenarios[0].id == "two-agents"


def test_actual_result_validates_against_result_schema(repository_root: Path) -> None:
    schema_path = repository_root / "contracts" / "simulation-result.schema.json"
    with schema_path.open(encoding="utf-8") as schema_file:
        schema: dict[str, Any] = json.load(schema_file)
    result = run_simulation(
        load_model(repository_root / "examples" / "support-deterministic.json")
    ).model_dump(mode="json", by_alias=True)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    Draft202012Validator(schema).validate(
        run_model(repository_root / "examples" / "support-deterministic.json")
    )


def test_actual_repeated_request_and_result_validate_against_schemas(
    repository_root: Path,
) -> None:
    request_schema = json.loads(
        (repository_root / "contracts" / "repeated-simulation-request.schema.json").read_text(
            encoding="utf-8"
        )
    )
    result_schema = json.loads(
        (repository_root / "contracts" / "repeated-simulation-result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    operational_schema = json.loads(
        (repository_root / "contracts" / "operational-model.schema.json").read_text(
            encoding="utf-8"
        )
    )
    single_result_schema = json.loads(
        (repository_root / "contracts" / "simulation-result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    registry = Registry().with_resources(
        [
            (
                operational_schema["$id"],
                Resource.from_contents(operational_schema),
            ),
            (
                single_result_schema["$id"],
                Resource.from_contents(single_result_schema),
            ),
        ]
    )
    request = RepeatedSimulationRequest(
        model=load_model(repository_root / "examples" / "support-deterministic.json"),
        baseSeed=42,
        runCount=2,
        representativeRun={"detailMode": "summary", "sampledItemLimit": None},
    )
    result = run_repeated_simulation(request)

    Draft202012Validator.check_schema(request_schema)
    Draft202012Validator.check_schema(result_schema)
    Draft202012Validator(request_schema, registry=registry).validate(
        request.model_dump(mode="json", by_alias=True, exclude_none=True)
    )
    Draft202012Validator(result_schema, registry=registry).validate(
        result.model_dump(mode="json", by_alias=True)
    )


def test_actual_comparison_request_and_result_validate_against_schemas(
    repository_root: Path,
) -> None:
    request_schema = json.loads(
        (repository_root / "contracts" / "scenario-comparison-request.schema.json").read_text(
            encoding="utf-8"
        )
    )
    result_schema = json.loads(
        (repository_root / "contracts" / "scenario-comparison-result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    operational_schema = json.loads(
        (repository_root / "contracts" / "operational-model.schema.json").read_text(
            encoding="utf-8"
        )
    )
    single_result_schema = json.loads(
        (repository_root / "contracts" / "simulation-result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    registry = Registry().with_resources(
        [
            (operational_schema["$id"], Resource.from_contents(operational_schema)),
            (single_result_schema["$id"], Resource.from_contents(single_result_schema)),
        ]
    )
    model = load_model(repository_root / "examples" / "support-deterministic.json")
    request = ScenarioComparisonRequest.model_validate(
        {
            "baselineModel": model,
            "scenarios": [
                {
                    "id": "capacity",
                    "name": "Capacity",
                    "overrides": [
                        {
                            "entityType": "resourcePool",
                            "entityId": "agents",
                            "field": "capacity",
                            "value": 2,
                        }
                    ],
                }
            ],
            "execution": {"baseSeed": 42, "runCount": 2},
            "objective": {"metric": "averageCycleTime", "direction": "minimize"},
            "representativeEvidence": {
                "detailMode": "summary",
                "sampledItemLimit": None,
            },
        }
    )
    result = run_scenario_comparison(request)

    Draft202012Validator.check_schema(request_schema)
    Draft202012Validator.check_schema(result_schema)
    Draft202012Validator(request_schema, registry=registry).validate(
        request.model_dump(mode="json", by_alias=True, exclude_none=True)
    )
    Draft202012Validator(result_schema, registry=registry).validate(
        result.model_dump(mode="json", by_alias=True)
    )
