from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.engine.integrity import SimulationIntegrityError
from app.engine.repeated import RepeatedSimulationError
from app.scenarios.coordinator import ScenarioComparisonError


def request_for(model: dict[str, Any], **overrides: object) -> dict[str, object]:
    request: dict[str, object] = {"schemaVersion": "0.3.0", "model": model}
    request.update(overrides)
    return request


def comparison_request_for(model: dict[str, Any]) -> dict[str, object]:
    return {
        "schemaVersion": "0.5.0",
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
                        "operation": "replace",
                        "value": 2,
                    }
                ],
            }
        ],
        "execution": {"baseSeed": 42, "runCount": 2},
        "objective": {"metric": "averageCycleTime", "direction": "minimize"},
        "representativeEvidence": {
            "baseline": True,
            "topRankedScenario": True,
            "detailMode": "summary",
            "sampledItemLimit": None,
        },
    }


def test_simulate_defaults_to_typed_summary_result(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(main_module.app).post(
        "/api/simulation/simulate",
        json=request_for(
            deterministic_model_data,
            runLabel="api-regression",
            seedOverride=42,
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == "0.3.0"
    assert payload["run"]["seed"] == 42
    assert payload["run"]["runLabel"] == "api-regression"
    assert payload["systemMetrics"]["averageWaitingTime"] == 6
    assert payload["resultDetail"]["mode"] == "summary"
    assert payload["resultDetail"]["includedEventCount"] == 0
    assert payload["events"] == []


@pytest.mark.parametrize(
    "detail",
    [
        {"mode": "summary"},
        {"mode": "sampled", "sampledItemLimit": 2},
        {"mode": "full"},
    ],
)
def test_simulate_supports_each_result_detail_mode(
    deterministic_model_data: dict[str, Any], detail: dict[str, object]
) -> None:
    response = TestClient(main_module.app).post(
        "/api/simulation/simulate",
        json=request_for(deterministic_model_data, resultDetail=detail),
    )

    assert response.status_code == 200
    assert response.json()["resultDetail"]["mode"] == detail["mode"]


def test_simulate_is_reproducible(deterministic_model_data: dict[str, Any]) -> None:
    request = request_for(deterministic_model_data, seedOverride=77)
    client = TestClient(main_module.app)

    assert client.post("/api/simulation/simulate", json=request).json() == client.post(
        "/api/simulation/simulate", json=request
    ).json()


def test_simulate_rejects_invalid_model(deterministic_model_data: dict[str, Any]) -> None:
    deterministic_model_data["resourcePools"] = []

    response = TestClient(main_module.app).post(
        "/api/simulation/simulate", json=request_for(deterministic_model_data)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MODEL_VALIDATION_FAILED"
    assert response.json()["error"]["fieldErrors"]


def test_simulate_rejects_invalid_detail_combination(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(main_module.app).post(
        "/api/simulation/simulate",
        json=request_for(
            deterministic_model_data,
            resultDetail={"mode": "summary", "sampledItemLimit": 2},
        ),
    )

    assert response.status_code == 422


def test_integrity_failure_returns_safe_structured_server_error(
    deterministic_model_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_integrity(*args: object, **kwargs: object) -> None:
        raise SimulationIntegrityError("test_failure", "private diagnostic")

    monkeypatch.setattr(main_module, "run_simulation", fail_integrity)
    response = TestClient(main_module.app).post(
        "/api/simulation/simulate", json=request_for(deterministic_model_data)
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "SIMULATION_INTEGRITY_FAILED",
            "message": "The simulation evidence failed its integrity checks.",
            "fieldErrors": [],
            "details": {},
        }
    }


def test_repeated_simulation_endpoint_is_typed_and_reproducible(
    deterministic_model_data: dict[str, Any],
) -> None:
    request = {
        "schemaVersion": "0.4.0",
        "model": deterministic_model_data,
        "baseSeed": 42,
        "runCount": 2,
        "representativeRun": {"detailMode": "summary", "sampledItemLimit": None},
    }
    client = TestClient(main_module.app)

    first = client.post("/api/simulation/simulate/repeated", json=request)
    second = client.post("/api/simulation/simulate/repeated", json=request)

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["schemaVersion"] == "0.4.0"
    assert first.json()["successfulRunCount"] == 2
    assert first.json()["representativeRun"]["rerunSnapshotMatches"] is True


def test_repeated_simulation_rejects_invalid_request(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(main_module.app).post(
        "/api/simulation/simulate/repeated",
        json={
            "schemaVersion": "0.4.0",
            "model": deterministic_model_data,
            "baseSeed": 42,
            "runCount": 1,
        },
    )

    assert response.status_code == 422


def test_repeated_batch_failure_returns_safe_error(
    deterministic_model_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_batch(*args: object, **kwargs: object) -> None:
        raise RepeatedSimulationError("private", "private diagnostics")

    monkeypatch.setattr(main_module, "run_repeated_simulation", fail_batch)
    response = TestClient(main_module.app).post(
        "/api/simulation/simulate/repeated",
        json={
            "schemaVersion": "0.4.0",
            "model": deterministic_model_data,
            "baseSeed": 42,
            "runCount": 2,
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "REPEATED_SIMULATION_FAILED",
            "message": "The repeated simulation could not produce sufficient evidence.",
            "fieldErrors": [],
            "details": {},
        }
    }


def test_scenario_comparison_endpoint_is_typed_and_reproducible(
    deterministic_model_data: dict[str, Any],
) -> None:
    request = comparison_request_for(deterministic_model_data)
    client = TestClient(main_module.app)

    first = client.post("/api/simulation/compare/scenarios", json=request)
    second = client.post("/api/simulation/compare/scenarios", json=request)

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["schemaVersion"] == "0.5.0"
    assert first.json()["rankingLabel"] == "comparative ranking"


def test_scenario_comparison_failure_returns_safe_error(
    deterministic_model_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_comparison(*args: object, **kwargs: object) -> None:
        raise ScenarioComparisonError("private", "private diagnostics")

    monkeypatch.setattr(main_module, "run_scenario_comparison", fail_comparison)
    response = TestClient(main_module.app).post(
        "/api/simulation/compare/scenarios",
        json=comparison_request_for(deterministic_model_data),
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "COMPARISON_FAILED",
            "message": "The comparison could not be completed.",
            "fieldErrors": [],
            "details": {},
        }
    }


def test_request_validation_uses_stable_product_error_envelope() -> None:
    response = TestClient(main_module.app).post(
        "/api/simulation/compare/scenarios", json={}
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert payload["error"]["message"] == "Check the highlighted request fields."
    assert payload["error"]["fieldErrors"]
    assert payload["error"]["details"] == {}
    assert "pydantic" not in str(payload).lower()


def test_work_budget_rejection_uses_safe_structured_details(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model_data["sources"][0]["itemCount"] = 1000
    request = comparison_request_for(deterministic_model_data)
    request["execution"] = {"baseSeed": 42, "runCount": 500}
    request["scenarios"] = [
        {
            "id": f"capacity-{index}",
            "name": f"Capacity {index}",
            "overrides": [
                {
                    "entityType": "resourcePool",
                    "entityId": "agents",
                    "field": "capacity",
                    "operation": "replace",
                    "value": index + 2,
                }
            ],
        }
        for index in range(5)
    ]

    response = TestClient(main_module.app).post(
        "/api/simulation/compare/scenarios", json=request
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "WORK_BUDGET_EXCEEDED",
            "message": "This comparison is too large for synchronous execution.",
            "fieldErrors": [],
            "details": {
                "estimatedWorkUnits": 3_000_000,
                "maximumWorkUnits": 100_000,
            },
        }
    }


@pytest.mark.parametrize(
    ("internal_code", "public_code", "message"),
    [
        (
            "baseline_execution_failed",
            "BASELINE_EXECUTION_FAILED",
            "The baseline simulation could not be completed.",
        ),
        (
            "comparison_integrity_failed",
            "COMPARISON_INTEGRITY_FAILED",
            "The comparison evidence failed its integrity checks.",
        ),
    ],
)
def test_comparison_failure_categories_map_to_stable_public_codes(
    deterministic_model_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    internal_code: str,
    public_code: str,
    message: str,
) -> None:
    def fail_comparison(*args: object, **kwargs: object) -> None:
        raise ScenarioComparisonError(internal_code, "private path C:\\private")

    monkeypatch.setattr(main_module, "run_scenario_comparison", fail_comparison)
    response = TestClient(main_module.app).post(
        "/api/simulation/compare/scenarios",
        json=comparison_request_for(deterministic_model_data),
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": public_code,
            "message": message,
            "fieldErrors": [],
            "details": {},
        }
    }


def test_unexpected_server_failure_is_safe(
    deterministic_model_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_unexpected(*args: object, **kwargs: object) -> None:
        raise RuntimeError("private path C:\\private")

    monkeypatch.setattr(main_module, "run_scenario_comparison", fail_unexpected)
    response = TestClient(
        main_module.app, raise_server_exceptions=False
    ).post(
        "/api/simulation/compare/scenarios",
        json=comparison_request_for(deterministic_model_data),
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "The service encountered an unexpected error.",
            "fieldErrors": [],
            "details": {},
        }
    }


def test_legacy_unprefixed_simulation_routes_are_not_public(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(main_module.app).post(
        "/simulate", json=request_for(deterministic_model_data)
    )

    assert response.status_code == 404
