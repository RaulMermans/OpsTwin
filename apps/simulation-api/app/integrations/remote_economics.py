from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.economics.decision import DecisionError, DecisionEvaluationRequest, evaluate_decision
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


@router.post("/evaluate-economics")
async def evaluate_economics_remote(request: Request) -> JSONResponse:
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
                "operation": "evaluate-economics",
                "reason": "fit",
                "header": sanitize_remote_log(request.headers.get("authorization")),
            },
        )
        return _error(401, "FIT_INVALID", "The Forge Invocation Token could not be verified.")
    emit(
        "remote.authentication.accepted",
        {
            "correlationId": correlation_id,
            "operation": "evaluate-economics",
            "installationRef": _installation_ref(str(verified["installationId"])),
            "contractVersion": "cg6.v1",
        },
    )
    try:
        payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(400, "INVALID_JSON", "The request body is not valid JSON.")
    if not isinstance(payload, dict):
        return _error(400, "INVALID_JSON", "The request body must be a JSON object.")
    forbidden = {"baselineModel", "model", "issues", "jira", "oauth", "token", "snapshot", "cases"}
    if forbidden.intersection(payload):
        emit(
            "economics.blocked",
            {
                "correlationId": correlation_id,
                "reason": "non_synthetic",
                "operation": "evaluate-economics",
            },
        )
        return _error(
            403,
            "NON_SYNTHETIC_REJECTED",
            "Remote economic evaluation accepts synthetic experiment evidence only.",
        )
    try:
        evaluation_request = DecisionEvaluationRequest.model_validate(payload)
    except ValidationError:
        return _error(422, "REQUEST_VALIDATION_FAILED", "Check the highlighted request fields.")
    try:
        result = evaluate_decision(evaluation_request)
    except DecisionError as error:
        emit(
            "economics.refused",
            {"correlationId": correlation_id, "reason": error.code, "operation": "evaluate-economics"},  # noqa: E501
        )
        return _error(422, error.code.upper(), error.message)
    duration_ms = int((time.perf_counter() - started) * 1000)
    body = result.model_dump(by_alias=True, exclude_none=True)
    body["durationMs"] = duration_ms
    body["correlationId"] = correlation_id
    if body.get("synthetic") is not True or body.get("integrityStatus") != "passed":
        return _error(500, "RESPONSE_VALIDATION_FAILED", "Economic response contract was invalid.")
    emit(
        "economics.completed",
        {
            "correlationId": correlation_id,
            "durationMs": duration_ms,
            "fixtureId": evaluation_request.fixture_id,
            "synthetic": True,
        },
    )
    return JSONResponse(content=body)
