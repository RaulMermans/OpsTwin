from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.calibration.construct import ConstructionError
from app.integrations.baselines import (
    BaselineConstructRequest,
    BaselineError,
    construct_baseline,
    public_calibration,
)
from app.integrations.csv_events import CsvImportError
from app.integrations.evidence_token import EvidenceTokenError, sign_claims
from app.integrations.fit import (
    FitValidationError,
    assert_payload_bounds,
    environment_type_from_verified,
    sanitize_remote_log,
    trusted_app_id,
    verify_forge_invocation_token,
)
from app.integrations.remote_compare import _error, _installation_ref
from app.integrations.telemetry import emit

router = APIRouter(prefix="/api/integrations/atlassian/v1")


@router.post("/construct-baseline")
async def construct_baseline_remote(request: Request) -> JSONResponse:
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
                "operation": "construct-baseline",
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
    if {"model", "issues", "jira", "oauth", "token", "baselineModel"}.intersection(payload):
        return _error(403, "UNTRUSTED_MODEL_REJECTED", "Arbitrary models and source records are not accepted.")  # noqa: E501
    try:
        construct_request = BaselineConstructRequest.model_validate(payload)
    except ValidationError:
        return _error(422, "REQUEST_VALIDATION_FAILED", "Check the highlighted request fields.")
    try:
        artifact, extra = construct_baseline(construct_request)
    except BaselineError as error:
        return _error(422, error.code.upper(), error.message)
    except CsvImportError as error:
        return _error(422, error.code.upper(), error.message)
    except ConstructionError as error:
        return _error(422, error.code.upper(), error.message)
    duration_ms = int((time.perf_counter() - started) * 1000)
    extra["durationMs"] = duration_ms
    extra["correlationId"] = correlation_id
    if artifact is None:
        extra["baselineToken"] = None
        return JSONResponse(content=extra)
    body = public_calibration(artifact, extra)
    reconstruction = construct_request.model_dump(by_alias=True, exclude_none=True)
    reconstruction.pop("csvText", None)
    if construct_request.source_mode in {"jira", "csv"} and extra.get("snapshot"):
        reconstruction["snapshot"] = extra["snapshot"]
    try:
        body["baselineToken"] = sign_claims(
            {
                "kind": "baseline",
                "appId": trusted_app_id(),
                "installationId": verified["installationId"],
                "environmentType": environment_type_from_verified(verified),
                "sourceMode": construct_request.source_mode,
                "modelFingerprint": artifact.model_fingerprint,
                "reconstruction": reconstruction,
            }
        )
    except EvidenceTokenError as error:
        return _error(500, error.code.upper(), error.message)
    emit(
        "baseline.completed",
        {
            "correlationId": correlation_id,
            "sourceMode": construct_request.source_mode,
            "durationMs": duration_ms,
            "installationRef": _installation_ref(str(verified["installationId"])),
        },
    )
    return JSONResponse(content=body)
