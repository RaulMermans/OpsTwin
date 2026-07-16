from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_expected_payload() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "opstwin-simulation-api",
    }


def test_prefixed_health_returns_expected_payload() -> None:
    response = TestClient(app).get("/api/simulation/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "opstwin-simulation-api",
    }
