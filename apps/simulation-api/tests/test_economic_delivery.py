import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.cli import run_economic_request, run_economic_sensitivity_request
from app.main import app


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_economic_api_cli_and_contract_are_in_parity(repository_root: Path) -> None:
    request_path = (
        repository_root / "examples" / "product" / "support-economic-comparison-request.json"
    )
    request = load(request_path)
    response = TestClient(app).post("/api/simulation/analyze/economics", json=request)

    assert response.status_code == 200
    cli = run_economic_request(request_path)
    payload = response.json()
    assert payload == cli
    Draft202012Validator(
        load(repository_root / "contracts" / "economic-comparison-request.schema.json")
    ).validate(request)
    Draft202012Validator(
        load(repository_root / "contracts" / "economic-comparison-result.schema.json")
    ).validate(payload)


def test_economic_sensitivity_api_cli_and_contract_are_in_parity(
    repository_root: Path,
) -> None:
    request_path = (
        repository_root / "examples" / "product" / "support-economic-sensitivity-request.json"
    )
    request = load(request_path)
    response = TestClient(app).post("/api/simulation/analyze/economic-sensitivity", json=request)

    assert response.status_code == 200
    cli = run_economic_sensitivity_request(request_path)
    payload = response.json()
    assert payload == cli
    Draft202012Validator(
        load(repository_root / "contracts" / "economic-sensitivity-request.schema.json")
    ).validate(request)
    Draft202012Validator(
        load(repository_root / "contracts" / "economic-sensitivity-result.schema.json")
    ).validate(response.json())


def test_invalid_economic_assumptions_fail_before_simulation(repository_root: Path) -> None:
    request = load(
        repository_root / "examples" / "product" / "support-economic-comparison-request.json"
    )
    request["assumptions"]["currency"] = "euro"

    response = TestClient(app).post("/api/simulation/analyze/economics", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


def test_economic_result_schema_rejects_unknown_nested_fields(repository_root: Path) -> None:
    request = load(
        repository_root / "examples" / "product" / "support-economic-comparison-request.json"
    )
    payload = TestClient(app).post("/api/simulation/analyze/economics", json=request).json()
    payload["scenarios"][0]["intervention"]["unexpected"] = True

    validator = Draft202012Validator(
        load(repository_root / "contracts" / "economic-comparison-result.schema.json")
    )
    assert not validator.is_valid(payload)
