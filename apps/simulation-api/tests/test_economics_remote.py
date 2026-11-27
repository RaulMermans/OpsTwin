from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.integrations import remote_economics
from app.main import app

PATH = "/api/integrations/atlassian/v1/evaluate-economics"
INSTALLATION_ID = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"


@pytest.fixture
def authorized(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(
        remote_economics,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {"installationId": INSTALLATION_ID, "payload": {}},
    )
    yield


def test_unauthenticated_economics_is_rejected() -> None:
    response = TestClient(app).post(PATH, json={"contractVersion": "cg6.v1"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "FIT_INVALID"


def test_snapshot_payloads_are_rejected(authorized: None) -> None:
    response = TestClient(app).post(
        PATH,
        json={"contractVersion": "cg6.v1", "snapshot": {"cases": []}, "fixtureId": "cg5-hybrid-support"},  # noqa: E501
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NON_SYNTHETIC_REJECTED"
