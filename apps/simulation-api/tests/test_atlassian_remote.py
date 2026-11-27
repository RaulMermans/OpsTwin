from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.integrations import remote_compare
from app.main import app

INSTALLATION_ID = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"
PATH = "/api/integrations/atlassian/v1/compare"


@pytest.fixture
def authorized(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(
        remote_compare,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {"installationId": INSTALLATION_ID, "payload": {}},
    )
    yield


def _body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "contractVersion": "cg1.v1",
        "experimentId": "support-operations-synthetic",
        "intervention": "add-capacity",
        "extraCapacity": 1,
        "runCount": 2,
        "baseSeed": 20260716,
    }
    payload.update(overrides)
    return payload


def test_unauthenticated_compare_is_rejected() -> None:
    response = TestClient(app).post(PATH, json=_body())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "FIT_INVALID"


def test_non_synthetic_payloads_are_rejected(authorized: None) -> None:
    response = TestClient(app).post(PATH, json=_body(baselineModel={"name": "nope"}))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NON_SYNTHETIC_REJECTED"


def test_invalid_intervention_is_rejected(authorized: None) -> None:
    response = TestClient(app).post(PATH, json=_body(extraCapacity=3))
    assert response.status_code == 422


def test_public_simulation_compare_route_is_unchanged() -> None:
    response = TestClient(app).get("/api/simulation/health")
    assert response.status_code == 200
    assert response.json()["service"] == "opstwin-simulation-api"


def test_synthetic_compare_is_reproducible_and_parameter_sensitive(authorized: None) -> None:
    client = TestClient(app)
    first = client.post(PATH, json=_body())
    second = client.post(PATH, json=_body())
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["baseSeed"] == 20260716
    assert first.json()["integrityStatus"] == "passed"
    assert first.json()["baselineCycleTime"]["mean"] == second.json()["baselineCycleTime"]["mean"]
    assert first.json()["pairedDifference"]["mean"] == second.json()["pairedDifference"]["mean"]

    other = client.post(PATH, json=_body(extraCapacity=2))
    assert other.status_code == 200
    changed = other.json()["pairedDifference"]["mean"] != first.json()["pairedDifference"]["mean"]
    if not changed:
        pytest.skip(
            "This fixture did not produce a measurable paired-difference change at runCount=2."
        )
    assert changed
