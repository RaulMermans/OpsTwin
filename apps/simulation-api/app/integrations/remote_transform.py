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
from app.calibration.contracts import CalibrationArtifact
from app.calibration.workflow import calibrate
from app.domain.models import ContractModel
from app.integrations.baselines import BaselineError, reconstruct_from_claims
from app.integrations.evidence_token import (
    EvidenceTokenError,
    artifact_claims,
    authorized_scope_from_payload,
    bind_context,
    bind_request_principal,
    compact_operational_evidence,
    sign_claims,
    verify_claims,
)
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
SourceMode = Literal["synthetic", "manual", "jira", "csv"]
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
    fixture_id: FixtureId | None = None
    source_mode: SourceMode = "synthetic"
    baseline_token: str | None = None
    approve_lab_assumptions: bool = False
    random_seed: int = 20_260_327
    intervention: InterventionConfig | None = None
    alternatives: list[NamedAlternative] | None = Field(default=None, max_length=3)
    execution: ExperimentExecution = ExperimentExecution()
    experiment_id: str | None = Field(default=None, max_length=128)
    request_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def require_catalog_mode(self) -> AtlassianTransformRequest:
        if self.source_mode != "synthetic" and not self.baseline_token:
            raise ValueError("user-defined baselines require a signed baseline token")
        if self.source_mode == "synthetic" and self.fixture_id is None and not self.baseline_token:
            raise ValueError("synthetic experiments require fixtureId")
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
            {"correlationId": correlation_id, "reason": "untrusted_model", "operation": "transform"},  # noqa: E501
        )
        return _error(
            403,
            "UNTRUSTED_MODEL_REJECTED",
            "Remote experiments reconstruct baselines from signed tokens or synthetic fixtures only.",  # noqa: E501
        )
    try:
        project_key, principal_id = authorized_scope_from_payload(payload)
        principal_id = bind_request_principal(verified, principal_id)
        payload.pop("authorizedProjectKey", None)
        payload.pop("authorizedPrincipal", None)
        transform_request = AtlassianTransformRequest.model_validate(payload)
    except EvidenceTokenError as error:
        return _error(422, error.code.upper(), error.message)
    except ValidationError:
        return _error(422, "REQUEST_VALIDATION_FAILED", "Check the highlighted request fields.")
    environment_type = environment_type_from_verified(verified)

    def _artifact() -> tuple[CalibrationArtifact, SourceMode, bool]:
        if transform_request.baseline_token:
            claims = verify_claims(transform_request.baseline_token)
            bind_context(
                claims,
                app_id=trusted_app_id(),
                installation_id=str(verified["installationId"]),
                environment_type=environment_type,
                project_key=project_key,
                principal_id=principal_id,
                kind="baseline",
                purpose="transform",
            )
            token_mode = claims.get("sourceMode")
            if token_mode not in {"synthetic", "manual", "jira", "csv"}:
                raise EvidenceTokenError(
                    "scope_mismatch",
                    "Signed baseline evidence is missing a valid source mode.",
                )
            if token_mode != transform_request.source_mode:
                raise EvidenceTokenError(
                    "scope_mismatch",
                    "Requested source mode does not match signed baseline evidence.",
                )
            artifact = reconstruct_from_claims(claims)
            source_mode = transform_request.source_mode
            provenance = artifact.provenance or {}
            synthetic = (
                claims.get("synthetic") is True
                or source_mode == "synthetic"
                or provenance.get("evidenceClass") == "synthetic"
            )
            return artifact, source_mode, synthetic
        assert transform_request.fixture_id is not None
        if transform_request.fixture_id not in LABORATORY_FIXTURES:
            raise KeyError(transform_request.fixture_id)
        snapshot = load_fixture(transform_request.fixture_id, transform_request.random_seed)
        engine_request = request_for_fixture(
            transform_request.fixture_id,
            snapshot,
            approve=transform_request.approve_lab_assumptions,
        )
        return calibrate(snapshot, engine_request), "synthetic", True

    def _execute() -> InterventionEvidence | MultiExperimentEvidence:
        artifact, source_mode, synthetic = _artifact()
        if transform_request.contract_version == "cg5.v1":
            assert transform_request.alternatives is not None
            return run_multi_intervention_experiment(
                artifact,
                transform_request.alternatives,
                transform_request.execution,
                fixture_id=transform_request.fixture_id,
                experiment_id=transform_request.experiment_id or str(uuid.uuid4()),
                request_id=transform_request.request_id,
                source_mode=source_mode,
                synthetic=synthetic,
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
    except (EvidenceTokenError, BaselineError) as error:
        return _error(422, error.code.upper(), error.message)
    except KeyError:
        return _error(422, "UNKNOWN_FIXTURE", "The fixture identifier is not in the synthetic catalog.")  # noqa: E501
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
            "synthetic": getattr(evidence, "synthetic", True),
        },
    )
    body = evidence.model_dump(by_alias=True, exclude_none=True)
    if body.get("synthetic") is True:
        body["disclosure"] = "Synthetic laboratory experiment. Not this Jira project's history."
    elif body.get("sourceMode") == "manual":
        body["disclosure"] = "User-defined exploratory experiment. Not historically calibrated."
    elif body.get("sourceMode") == "csv":
        body["disclosure"] = "CSV-sourced exploratory experiment. Not independently audited history."  # noqa: E501
    else:
        body["disclosure"] = "Source-linked experiment. Import success is not historical validation."  # noqa: E501
    if body.get("identitiesAgree") is not True:
        return _error(500, "RESPONSE_VALIDATION_FAILED", "Transform response contract was invalid.")
    try:
        body["evidenceToken"] = sign_claims(
            artifact_claims(
                kind="experiment",
                purpose="evaluate",
                app_id=trusted_app_id(),
                installation_id=str(verified["installationId"]),
                environment_type=environment_type,
                project_key=project_key,
                principal_id=principal_id,
                extra={
                    "sourceMode": getattr(evidence, "source_mode", None)
                    or transform_request.source_mode,
                    "experimentIdentity": body.get("experimentIdentity"),
                    "evidence": compact_operational_evidence(evidence)
                    if isinstance(evidence, MultiExperimentEvidence)
                    else body,
                },
            )
        )
    except EvidenceTokenError as error:
        return _error(500, error.code.upper(), error.message)
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
