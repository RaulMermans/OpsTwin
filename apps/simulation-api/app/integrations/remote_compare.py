from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.integrations.experiment import AtlassianCompareRequest, run_synthetic_comparison
from app.integrations.fit import (
    FitValidationError,
    assert_payload_bounds,
    sanitize_remote_log,
    trusted_app_id,
    verify_forge_invocation_token,
)
from app.integrations.telemetry import emit
from app.scenarios.coordinator import ComparisonWorkBudgetError, ScenarioComparisonError

router = APIRouter(prefix="/api/integrations/atlassian/v1")


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "fieldErrors": [], "details": {}}},
    )


def _installation_ref(installation_id: str) -> str:
    digest = hashlib.sha256(installation_id.encode("utf-8")).hexdigest()[:16]
    return f"install:{digest}"


@router.post("/compare")
async def compare(request: Request) -> JSONResponse:
    correlation_id = str(uuid.uuid4())
    started = time.perf_counter()
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        emit(
            "remote.authentication.rejected",
            {"correlationId": correlation_id, "operation": "compare", "reason": "content_type"},
        )
        return _error(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json.")

    raw = await request.body()
    try:
        assert_payload_bounds(raw)
    except FitValidationError:
        emit(
            "remote.authentication.rejected",
            {
                "correlationId": correlation_id,
                "operation": "compare",
                "reason": "payload_too_large",
            },
        )
        return _error(413, "PAYLOAD_TOO_LARGE", "The request exceeds the remote payload limit.")

    try:
        verified = verify_forge_invocation_token(
            request.headers.get("authorization"),
            trusted_app_id(),
        )
    except FitValidationError as error:
        emit(
            "remote.authentication.rejected",
            {
                "correlationId": correlation_id,
                "operation": "compare",
                "reason": error.code,
                "header": sanitize_remote_log(request.headers.get("authorization")),
            },
        )
        return _error(401, "FIT_INVALID", "The Forge Invocation Token could not be verified.")

    installation_id = str(verified["installationId"])
    emit(
        "remote.authentication.accepted",
        {
            "correlationId": correlation_id,
            "operation": "compare",
            "installationRef": _installation_ref(installation_id),
            "contractVersion": "cg1.v1",
        },
    )

    try:
        payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(400, "INVALID_JSON", "The request body is not valid JSON.")

    if not isinstance(payload, dict):
        return _error(400, "INVALID_JSON", "The request body must be a JSON object.")
    forbidden = {"baselineModel", "model", "issues", "jira", "oauth", "token", "cases", "snapshot"}
    if forbidden.intersection(payload):
        emit(
            "simulation.request.validated",
            {
                "correlationId": correlation_id,
                "operation": "compare",
                "accepted": False,
                "reason": "non_synthetic",
            },
        )
        return _error(
            403,
            "NON_SYNTHETIC_REJECTED",
            "CG-1 remote comparisons accept synthetic catalog inputs only.",
        )

    try:
        compare_request = AtlassianCompareRequest.model_validate(payload)
    except ValidationError:
        emit(
            "simulation.request.validated",
            {
                "correlationId": correlation_id,
                "operation": "compare",
                "accepted": False,
                "reason": "schema",
            },
        )
        return _error(422, "REQUEST_VALIDATION_FAILED", "Check the highlighted request fields.")

    emit(
        "simulation.request.validated",
        {
            "correlationId": correlation_id,
            "operation": "compare",
            "accepted": True,
            "executionBudget": compare_request.run_count,
        },
    )
    emit("simulation.started", {"correlationId": correlation_id, "operation": "compare"})
    try:
        evidence = run_synthetic_comparison(compare_request)
    except ComparisonWorkBudgetError:
        emit(
            "simulation.failed",
            {"correlationId": correlation_id, "operation": "compare", "reason": "work_budget"},
        )
        return _error(
            422, "WORK_BUDGET_EXCEEDED", "This comparison is too large for synchronous execution."
        )
    except ScenarioComparisonError:
        emit(
            "simulation.failed",
            {"correlationId": correlation_id, "operation": "compare", "reason": "comparison"},
        )
        return _error(500, "COMPARISON_FAILED", "The comparison could not be completed.")
    except Exception:
        emit(
            "simulation.failed",
            {"correlationId": correlation_id, "operation": "compare", "reason": "internal"},
        )
        return _error(500, "INTERNAL_ERROR", "The service encountered an unexpected error.")

    duration_ms = int((time.perf_counter() - started) * 1000)
    emit(
        "simulation.completed",
        {
            "correlationId": correlation_id,
            "operation": "compare",
            "durationMs": duration_ms,
            "integrityStatus": evidence.integrity_status,
            "executionBudget": evidence.run_count,
        },
    )
    return JSONResponse(content=evidence.model_dump(by_alias=True, exclude_none=True))
