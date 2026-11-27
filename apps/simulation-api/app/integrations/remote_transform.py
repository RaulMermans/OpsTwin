from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, model_validator

from app.calibration.catalog import LABORATORY_FIXTURES, load_fixture, request_for_fixture
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
from app.interventions.catalog import (
    ExperimentExecution,
    InterventionConfig,
    InterventionError,
    NamedAlternative,
)
from app.interventions.execute import (
    InterventionEvidence,
    MultiExperimentEvidence,
    run_intervention_experiment,
    run_multi_intervention_experiment,
)
from app.scenarios.coordinator import ComparisonWorkBudgetError, ScenarioComparisonError

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
    "cg5-hybrid-support",
]


class AtlassianTransformRequest(ContractModel):
    contract_version: Literal["cg4.v1", "cg5.v1"] = "cg4.v1"
    fixture_id: FixtureId
    approve_lab_assumptions: bool = False
    random_seed: int = 20_260_327
    intervention: InterventionConfig | None = None
    alternatives: list[NamedAlternative] | None = Field(default=None, max_length=3)
    execution: ExperimentExecution = ExperimentExecution()
    experiment_id: str | None = Field(default=None, max_length=128)
    request_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def require_catalog_mode(self) -> AtlassianTransformRequest:
        if self.contract_version == "cg5.v1":
            if not self.alternatives:
                raise ValueError("cg5.v1 requires alternatives")
            if self.intervention is not None:
                raise ValueError("cg5.v1 uses alternatives rather than a single intervention")
            return self
        if self.intervention is None:
            raise ValueError("cg4.v1 requires one intervention")
        if self.alternatives:
            raise ValueError("cg4.v1 does not accept alternatives")
        return self


@router.post("/transform")
async def transform_remote(request: Request) -> JSONResponse:
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
                "operation": "transform",
                "reason": "fit",
                "header": sanitize_remote_log(request.headers.get("authorization")),
            },
        )
        return _error(401, "FIT_INVALID", "The Forge Invocation Token could not be verified.")
    emit(
        "remote.authentication.accepted",
        {
            "correlationId": correlation_id,
            "operation": "transform",
            "installationRef": _installation_ref(str(verified["installationId"])),
            "contractVersion": "cg5.v1",
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
            "transform.blocked",
            {"correlationId": correlation_id, "reason": "non_synthetic", "operation": "transform"},
        )
        return _error(
            403,
            "NON_SYNTHETIC_REJECTED",
            "Remote experiments accept synthetic fixture identifiers only.",
        )
    try:
        transform_request = AtlassianTransformRequest.model_validate(payload)
    except ValidationError:
        return _error(422, "REQUEST_VALIDATION_FAILED", "Check the highlighted request fields.")
    if transform_request.fixture_id not in LABORATORY_FIXTURES:
        return _error(
            422, "UNKNOWN_FIXTURE", "The fixture identifier is not in the synthetic catalog."
        )  # noqa: E501
    snapshot = load_fixture(transform_request.fixture_id, transform_request.random_seed)
    engine_request = request_for_fixture(
        transform_request.fixture_id,
        snapshot,
        approve=transform_request.approve_lab_assumptions,
    )

    def _execute() -> InterventionEvidence | MultiExperimentEvidence:
        artifact = calibrate(snapshot, engine_request)
        if transform_request.contract_version == "cg5.v1":
            assert transform_request.alternatives is not None
            return run_multi_intervention_experiment(
                artifact,
                transform_request.alternatives,
                transform_request.execution,
                fixture_id=transform_request.fixture_id,
                experiment_id=transform_request.experiment_id or str(uuid.uuid4()),
                request_id=transform_request.request_id,
            )
        assert transform_request.intervention is not None
        return run_intervention_experiment(
            artifact,
            transform_request.intervention,
            transform_request.execution,
            fixture_id=transform_request.fixture_id,
        )

    try:
        evidence = await asyncio.to_thread(_execute)
    except InterventionError as error:
        emit(
            "transform.refused",
            {"correlationId": correlation_id, "reason": error.code, "operation": "transform"},
        )
        return _error(422, error.code.upper(), error.message)
    except ComparisonWorkBudgetError:
        return _error(
            422, "WORK_BUDGET_EXCEEDED", "This comparison is too large for synchronous execution."
        )  # noqa: E501
    except ScenarioComparisonError:
        return _error(500, "COMPARISON_FAILED", "The comparison could not be completed.")
    duration_ms = int((time.perf_counter() - started) * 1000)
    emit(
        "transform.completed",
        {
            "correlationId": correlation_id,
            "fixtureId": transform_request.fixture_id,
            "kind": (
                "multi"
                if transform_request.intervention is None
                else transform_request.intervention.kind
            ),
            "durationMs": duration_ms,
            "integrityStatus": getattr(evidence, "integrity_status", None),
            "synthetic": True,
        },
    )
    body = evidence.model_dump(by_alias=True, exclude_none=True)
    body["disclosure"] = "Synthetic laboratory experiment. Not this Jira project's history."
    if body.get("synthetic") is not True or body.get("identitiesAgree") is not True:
        return _error(500, "RESPONSE_VALIDATION_FAILED", "Transform response contract was invalid.")
    if transform_request.contract_version == "cg5.v1":
        if body.get("contractVersion") != "cg5.v1":
            return _error(500, "RESPONSE_VALIDATION_FAILED", "Transform response contract was invalid.")  # noqa: E501
        if not body.get("experimentIdentity"):
            return _error(500, "RESPONSE_VALIDATION_FAILED", "Transform response contract was invalid.")  # noqa: E501
        if body.get("experimentStatus") == "complete":
            if body.get("integrityStatus") != "passed":
                return _error(
                    500,
                    "RESPONSE_VALIDATION_FAILED",
                    "A complete experiment cannot be returned without passed integrity.",
                )
            alternatives = body.get("alternatives") or []
            if any(item.get("status") != "valid" for item in alternatives):
                return _error(
                    500,
                    "RESPONSE_VALIDATION_FAILED",
                    "A complete experiment cannot include failed alternatives.",
                )
    return JSONResponse(content=body)
