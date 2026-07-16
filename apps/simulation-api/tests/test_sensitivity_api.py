from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_sensitivity_endpoint_returns_typed_result(
    deterministic_model_data: dict[str, Any],
) -> None:
    response = TestClient(app).post(
        "/api/simulation/analyze/sensitivity",
        json={
            "schemaVersion": "0.6.0",
            "baselineModel": deterministic_model_data,
            "target": {"entityType": "resourcePool", "entityId": "agents", "field": "capacity"},
            "values": [1, 2],
            "execution": {"baseSeed": 42, "runCount": 2},
            "metrics": ["averageCycleTime"],
        },
    )

    assert response.status_code == 200
    assert response.json()["schemaVersion"] == "0.6.0"
    assert response.json()["integrity"]["checksRun"] >= 18


def test_sensitivity_endpoint_uses_structured_work_budget_error(
    deterministic_model_data: dict[str, Any],
) -> None:
    deterministic_model_data["sources"][0]["itemCount"] = 1000
    response = TestClient(app).post(
        "/api/simulation/analyze/sensitivity",
        json={
            "schemaVersion": "0.6.0",
            "baselineModel": deterministic_model_data,
            "target": {"entityType": "resourcePool", "entityId": "agents", "field": "capacity"},
            "values": list(range(1, 11)),
            "execution": {"baseSeed": 42, "runCount": 100},
            "metrics": ["averageCycleTime"],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WORK_BUDGET_EXCEEDED"
