from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.integrations import remote_calibrate
from app.main import app

INSTALLATION_ID = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"
PATH = "/api/integrations/atlassian/v1/calibrate"
COMPARE = "/api/integrations/atlassian/v1/compare"


@pytest.fixture
def authorized(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(
        remote_calibrate,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {"installationId": INSTALLATION_ID, "payload": {}},
    )
    yield


def test_unauthenticated_calibrate_is_rejected() -> None:
    response = TestClient(app).post(PATH, json={"contractVersion": "cg3.v1", "fixtureId": "cg3-golden-analytical"})  # noqa: E501
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "FIT_INVALID"


def test_snapshot_payloads_are_rejected(authorized: None) -> None:
    response = TestClient(app).post(
        PATH,
        json={"contractVersion": "cg3.v1", "fixtureId": "cg3-golden-analytical", "snapshot": {"cases": []}},  # noqa: E501
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "OPERATIONAL_SNAPSHOT_REJECTED"


def test_compare_still_rejects_operational_snapshots(authorized: None, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: E501
    from app.integrations import remote_compare

    monkeypatch.setattr(
        remote_compare,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {"installationId": INSTALLATION_ID, "payload": {}},
    )
    response = TestClient(app).post(
        COMPARE,
        json={
            "contractVersion": "cg1.v1",
            "experimentId": "support-operations-synthetic",
            "intervention": "add-capacity",
            "extraCapacity": 1,
            "runCount": 2,
            "cases": [{"id": "OPS-1"}],
        },
    )
    assert response.status_code == 403


def test_synthetic_fixture_calibration_is_labeled(authorized: None) -> None:
    response = TestClient(app).post(
        PATH,
        json={"contractVersion": "cg3.v1", "fixtureId": "cg3-golden-analytical", "randomSeed": 21},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["synthetic"] is True
    assert "not this jira" in body["disclosure"].lower()
    assert body["fixtureId"] == "cg3-golden-analytical"
    assert "authorization" not in json_text(body)


def json_text(value: object) -> str:
    import json

    return json.dumps(value)
