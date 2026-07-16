import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from referencing import Registry, Resource

from app.main import app

ROOT = Path(__file__).resolve().parents[3]


def _schema(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def _request(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "0.6.0",
        "baselineModel": model,
        "target": {"entityType": "resourcePool", "entityId": "agents", "field": "capacity"},
        "values": [1, 2],
        "execution": {"baseSeed": 42, "runCount": 2},
        "metrics": ["averageCycleTime"],
    }


def test_sensitivity_api_result_validates_directly_against_published_schema(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(app).post(
        "/api/simulation/analyze/sensitivity", json=_request(deterministic_model_data)
    )

    assert response.status_code == 200
    Draft202012Validator(_schema("sensitivity-result.schema.json")).validate(response.json())


def test_sensitivity_result_schema_rejects_unknown_nested_fields(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(app).post(
        "/api/simulation/analyze/sensitivity", json=_request(deterministic_model_data)
    )
    payload = response.json()
    payload["target"]["unexpected"] = True

    with pytest.raises(SchemaValidationError):
        Draft202012Validator(_schema("sensitivity-result.schema.json")).validate(payload)


def test_sensitivity_result_schema_rejects_non_finite_nested_values(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(app).post(
        "/api/simulation/analyze/sensitivity", json=_request(deterministic_model_data)
    )
    payload = response.json()
    # JSON itself excludes NaN; the numeric bounds additionally reject infinities
    # when a non-conforming decoder supplies one as a Python extension.
    payload["responseCurves"][0]["points"][0]["mean"] = float("inf")

    with pytest.raises(SchemaValidationError):
        Draft202012Validator(_schema("sensitivity-result.schema.json")).validate(payload)


def test_sensitivity_contract_has_no_unconstrained_object_nodes() -> None:
    def walk(value: object, path: tuple[str, ...] = ()) -> list[str]:
        findings: list[str] = []
        if isinstance(value, dict):
            if value.get("type") == "object" and not any(
                key in value for key in ("properties", "additionalProperties", "patternProperties")
            ):
                findings.append("/".join(path))
            for key, child in value.items():
                findings.extend(walk(child, (*path, str(key))))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                findings.extend(walk(child, (*path, str(index))))
        return findings

    assert walk(_schema("sensitivity-result.schema.json")) == []


def test_canonical_sensitivity_example_request_and_result_validate() -> None:
    request = json.loads(
        (ROOT / "examples" / "product" / "support-sensitivity-request.json").read_text(
            encoding="utf-8"
        )
    )
    result = json.loads(
        (ROOT / "examples" / "product" / "support-sensitivity-result.json").read_text(
            encoding="utf-8"
        )
    )
    operational = _schema("operational-model.schema.json")
    registry = Registry().with_resource(
        operational["$id"], Resource.from_contents(operational)
    )

    Draft202012Validator(
        _schema("sensitivity-request.schema.json"), registry=registry
    ).validate(request)
    Draft202012Validator(_schema("sensitivity-result.schema.json")).validate(result)
