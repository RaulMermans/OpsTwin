import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def support_model_data(repository_root: Path) -> dict[str, Any]:
    path = repository_root / "examples" / "support-baseline.json"
    with path.open(encoding="utf-8") as model_file:
        value: dict[str, Any] = json.load(model_file)
    return value


@pytest.fixture
def deterministic_model_data() -> dict[str, Any]:
    return {
        "schemaVersion": "0.2.0",
        "name": "Deterministic Support Baseline",
        "timeUnit": "minutes",
        "runConfig": {"seed": 42},
        "sources": [
            {
                "id": "tickets",
                "name": "Ticket Source",
                "itemCount": 5,
                "initialArrivalTime": 0,
                "priority": 0,
                "firstStageId": "triage",
                "arrival": {"type": "fixed", "interval": 5},
            }
        ],
        "resourcePools": [{"id": "agents", "name": "Agents", "capacity": 1}],
        "stages": [
            {
                "id": "triage",
                "name": "Triage",
                "resourcePoolId": "agents",
                "processingTime": {"type": "fixed", "value": 8},
                "queuePolicy": "fifo",
            }
        ],
        "routes": [
            {
                "id": "triage-complete",
                "kind": "success",
                "fromStageId": "triage",
                "options": [
                    {"targetType": "completion", "probability": 1},
                ],
            }
        ],
        "slaRules": [{"id": "default", "targetDuration": 30}],
    }


@pytest.fixture(autouse=True)
def no_environment_mutation() -> Iterator[None]:
    yield
