from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.integrations import remote_transform
from app.main import app

INSTALLATION_ID = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"
PATH = "/api/integrations/atlassian/v1/transform"
SCOPE = {"authorizedProjectKey": "OPS", "authorizedPrincipal": "user-1"}


@pytest.fixture
def authorized(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(
        remote_transform,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {"installationId": INSTALLATION_ID, "payload": {}},
    )
    yield


def test_unauthenticated_transform_is_rejected() -> None:
    response = TestClient(app).post(
        PATH,
        json={
            "contractVersion": "cg4.v1",
            "fixtureId": "cg3-golden-analytical",
            "intervention": {
                "kind": "capacity",
                "extraTriageCapacity": 1,
                "extraResolutionCapacity": 0,
            },  # noqa: E501
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "FIT_INVALID"


def test_snapshot_payloads_are_rejected(authorized: None) -> None:
    response = TestClient(app).post(
        PATH,
        json={
            "contractVersion": "cg4.v1",
            "fixtureId": "cg3-golden-analytical",
            "snapshot": {"cases": []},
            "intervention": {"kind": "capacity", "extraResolutionCapacity": 1},
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "UNTRUSTED_MODEL_REJECTED"


def test_placeholder_item_count_cannot_be_requested(authorized: None) -> None:
    response = TestClient(app).post(
        PATH,
        json={
            "contractVersion": "cg4.v1",
            "fixtureId": "cg3-golden-analytical",
            "approveLabAssumptions": True,
            "randomSeed": 21,
            "intervention": {"kind": "capacity", "extraResolutionCapacity": 1},
            "execution": {"itemCount": 1, "runCount": 2, "baseSeed": 20261127},
            **SCOPE,
        },
    )
    assert response.status_code == 422


def test_synthetic_capacity_experiment_returns_paired_evidence(authorized: None) -> None:
    response = TestClient(app).post(
        PATH,
        json={
            "contractVersion": "cg4.v1",
            "fixtureId": "cg3-golden-analytical",
            "approveLabAssumptions": True,
            "randomSeed": 21,
            "intervention": {
                "kind": "capacity",
                "extraTriageCapacity": 1,
                "extraResolutionCapacity": 0,
            },  # noqa: E501
            "execution": {"itemCount": 20, "runCount": 2, "baseSeed": 20261127},
            **SCOPE,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["synthetic"] is True
    assert body["identitiesAgree"] is True
    assert body["experiment"]["itemCount"] == 20
    assert body["baselineInventory"]["canonicalItemCount"] == 1
    assert "not this jira" in body["disclosure"].lower()
    assert body["validPairedRunCount"] == 2
    assert "authorization" not in str(body).lower() or "Forge Invocation" not in str(body)


def test_multi_experiment_returns_shared_baseline_metrics(authorized: None) -> None:
    response = TestClient(app).post(
        PATH,
        json={
            "contractVersion": "cg5.v1",
            "fixtureId": "cg5-hybrid-support",
            "approveLabAssumptions": True,
            "randomSeed": 21,
            "experimentId": "demo-support-20261127",
            "requestId": "req-live-1",
            "alternatives": [
                {
                    "alternativeId": "human-expansion",
                    "intervention": {"kind": "capacity", "extraResolutionCapacity": 1},
                },
                {
                    "alternativeId": "ai-assisted",
                    "intervention": {
                        "kind": "ai_assisted",
                        "stageId": "triage",
                        "coverage": 0.5,
                        "processingReduction": 0.4,
                        "reviewOverheadMinutes": 0.25,
                    },
                },
            ],
            "execution": {"itemCount": 20, "runCount": 2, "baseSeed": 20261127},
            **SCOPE,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["contractVersion"] == "cg5.v1"
    assert body["experimentStatus"] == "complete"
    assert body["requestId"] == "req-live-1"
    assert body["baselineMetrics"]["averageCycleTime"]["unit"] == "minutes"
    assert len(body["alternatives"]) == 2
