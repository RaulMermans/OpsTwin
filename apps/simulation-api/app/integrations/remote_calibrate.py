from __future__ import annotations

import json
import time
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError

from app.calibration.catalog import FIXTURE_IDS, load_fixture, request_for_fixture
from app.calibration.workflow import calibrate
from app.domain.models import ContractModel
from app.integrations.fit import (
    FitValidationError,
    assert_payload_bounds,
    sanitize_remote_log,
    trusted_app_id,
    verify_forge_invocation_token,
)
from app.integrations.remote_compare import _error, _installation_ref
from app.integrations.telemetry import emit

router = APIRouter(prefix="/api/integrations/atlassian/v1")
FixtureId = Literal[
    "cg3-golden-analytical",
    "cg3-fully-observable",
    "cg3-partially-observable",
    "cg3-noisy",
    "cg3-nonstationary",
    "cg3-misspecified",
    "cg3-mixed-origin",
    "cg3-temporal-shift",
]


class AtlassianCalibrateRequest(ContractModel):
    contract_version: Literal["cg3.v1"] = "cg3.v1"
    fixture_id: FixtureId
    approve_lab_assumptions: bool = True
    random_seed: int = Field(default=20_260_327, ge=0, le=2**63 - 1)


@router.post("/calibrate")
async def calibrate_remote(request: Request) -> JSONResponse:
    correlation_id = str(uuid.uuid4())
    started = time.perf_counter()
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        return _error(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json.")
    raw = await request.body()
    try:
        assert_payload_bounds(raw)
    except FitValidationError:
        return _error(413, "PAYLOAD_TOO_LARGE", "The request exceeds the remote payload limit.")
    try:
        verified = verify_forge_invocation_token(
            request.headers.get("authorization"),
            trusted_app_id(),
        )
    except FitValidationError:
        emit(
            "remote.authentication.rejected",
            {
                "correlationId": correlation_id,
                "operation": "calibrate",
                "reason": "fit",
                "header": sanitize_remote_log(request.headers.get("authorization")),
            },
        )
        return _error(401, "FIT_INVALID", "The Forge Invocation Token could not be verified.")
    try:
        payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(400, "INVALID_JSON", "The request body is not valid JSON.")
    if not isinstance(payload, dict):
        return _error(400, "INVALID_JSON", "The request body must be a JSON object.")
    forbidden = {"baselineModel", "model", "issues", "jira", "oauth", "token", "snapshot", "cases"}
    if forbidden.intersection(payload):
        emit(
            "calibration.blocked",
            {"correlationId": correlation_id, "reason": "non_synthetic", "operation": "calibrate"},
        )
        return _error(
            403,
            "OPERATIONAL_SNAPSHOT_REJECTED",
            "CG-3 remote calibration accepts synthetic fixture identifiers only.",
        )
    try:
        calibrate_request = AtlassianCalibrateRequest.model_validate(payload)
    except ValidationError:
        return _error(422, "REQUEST_VALIDATION_FAILED", "Check the highlighted request fields.")
    if calibrate_request.fixture_id not in FIXTURE_IDS:
        return _error(422, "UNKNOWN_FIXTURE", "The fixture identifier is not in the synthetic catalog.")  # noqa: E501
    installation_id = str(verified["installationId"])
    emit(
        "remote.authentication.accepted",
        {
            "correlationId": correlation_id,
            "operation": "calibrate",
            "installationRef": _installation_ref(installation_id),
            "contractVersion": "cg3.v1",
        },
    )
    snapshot = load_fixture(calibrate_request.fixture_id, calibrate_request.random_seed)
    engine_request = request_for_fixture(
        calibrate_request.fixture_id,
        snapshot,
        approve=calibrate_request.approve_lab_assumptions,
    )
    artifact = calibrate(snapshot, engine_request)
    duration_ms = int((time.perf_counter() - started) * 1000)
    emit(
        "calibration.completed",
        {
            "correlationId": correlation_id,
            "fixtureId": calibrate_request.fixture_id,
            "readiness": artifact.readiness_status,
            "durationMs": duration_ms,
            "synthetic": True,
        },
    )
    body = artifact.model_dump(by_alias=True, exclude_none=True)
    body["synthetic"] = True
    body["fixtureId"] = calibrate_request.fixture_id
    body["disclosure"] = "Synthetic laboratory calibration. Not this Jira project's history."
    return JSONResponse(content=body)
