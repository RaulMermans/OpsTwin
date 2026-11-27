from __future__ import annotations

from typing import Any

from app.calibration.contracts import CalibrationRequest
from app.calibration.histories import (
    ProfileId,
    approved_capacity_and_service,
    default_mapping,
    generate_history,
)

FIXTURE_IDS: dict[str, ProfileId] = {
    "cg3-golden-analytical": "golden",
    "cg3-fully-observable": "observable",
    "cg3-partially-observable": "partial",
    "cg3-noisy": "noisy",
    "cg3-nonstationary": "nonstationary",
    "cg3-misspecified": "misspecified",
    "cg3-mixed-origin": "mixed",
    "cg3-temporal-shift": "shift",
}


def load_fixture(fixture_id: str, seed: int = 20260327) -> dict[str, Any]:
    profile = FIXTURE_IDS.get(fixture_id)
    if profile is None:
        raise KeyError(fixture_id)
    return generate_history(profile, seed)


def request_for_fixture(fixture_id: str, snapshot: dict[str, Any], *, approve: bool) -> CalibrationRequest:  # noqa: E501
    profile = FIXTURE_IDS[fixture_id]
    treat_worklogs = profile in {"golden", "observable"}
    mapping = default_mapping(reviewed=True, include_review=profile == "misspecified")
    payload: dict[str, Any] = {
        "snapshotReference": fixture_id,
        "snapshotFingerprint": snapshot["contentFingerprint"],
        "operationalMapping": mapping,
        "assumptionSet": approved_capacity_and_service() if approve else [],
        "estimationConfiguration": {
            "treatWorklogsAsProcessing": treat_worklogs,
            "allowAssumptionBasedModel": approve,
        },
        "randomSeed": 20260327,
    }
    return CalibrationRequest.model_validate(payload)
