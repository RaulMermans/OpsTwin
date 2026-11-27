from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from app.calibration.catalog import LABORATORY_FIXTURES, load_fixture, request_for_fixture
from app.calibration.contracts import CalibrationArtifact, CalibrationRequest
from app.calibration.manual import ManualBaselineSpec, construct_manual_artifact
from app.calibration.mapping import suggest_status_mapping
from app.calibration.snapshot import content_fingerprint, validate_snapshot_structure
from app.calibration.workflow import calibrate
from app.domain.models import ContractModel
from app.integrations.csv_events import parse_csv_event_log
from app.interventions.catalog import baseline_inventory, hybrid_compatible

SourceMode = Literal["synthetic", "manual", "jira", "csv"]


class BaselineError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BaselineConstructRequest(ContractModel):
    contract_version: Literal["cg7.v1"] = "cg7.v1"
    source_mode: SourceMode
    fixture_id: str | None = None
    approve_lab_assumptions: bool = False
    random_seed: int = Field(default=20_260_327, ge=0, le=2**63 - 1)
    manual: ManualBaselineSpec | None = None
    snapshot: dict[str, Any] | None = None
    csv_text: str | None = None
    calibration: CalibrationRequest | None = None

    @model_validator(mode="after")
    def matching_source(self) -> BaselineConstructRequest:
        if self.source_mode == "synthetic" and not self.fixture_id:
            raise ValueError("synthetic baselines require fixtureId")
        if self.source_mode == "manual" and self.manual is None:
            raise ValueError("manual baselines require a parameter specification")
        if self.source_mode == "jira" and self.snapshot is None:
            raise ValueError("Jira baselines require a minimized operational snapshot")
        if self.source_mode == "csv" and self.csv_text is None and self.snapshot is None:
            raise ValueError("CSV baselines require csvText or a normalized snapshot")
        return self


def public_calibration(artifact: CalibrationArtifact, extra: dict[str, Any]) -> dict[str, Any]:
    body = artifact.model_dump(by_alias=True, exclude_none=True)
    body["constructedModel"] = artifact.constructed_model is not None
    if artifact.constructed_model is not None:
        body["hybridCompatible"] = hybrid_compatible(artifact.constructed_model)
        body["baselineInventory"] = baseline_inventory(artifact.constructed_model)
    else:
        body["hybridCompatible"] = False
    body.update(extra)
    return body


def minimize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    def keep(item: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
        return {key: value for key, value in item.items() if key in allowed}

    case_fields = {
        "caseId",
        "sourceReference",
        "projectReference",
        "requestTypeReference",
        "priorityReference",
        "currentStatusReference",
        "createdAt",
        "resolvedAt",
        "createdAtInvalid",
        "observationStatus",
        "syntheticOrigin",
        "originUnknown",
        "reopened",
    }
    event_fields = {
        "eventId",
        "caseId",
        "eventType",
        "occurredAt",
        "observedAt",
        "previousValue",
        "newValue",
        "sourceReference",
        "durationMinutes",
        "provenance",
    }
    minimized = dict(snapshot)
    minimized["cases"] = [keep(item, case_fields) for item in snapshot.get("cases") or []]
    minimized["events"] = [keep(item, event_fields) for item in snapshot.get("events") or []]
    minimized["contentFingerprint"] = content_fingerprint(minimized)
    return minimized


def _source_snapshot(request: BaselineConstructRequest) -> dict[str, Any]:
    if request.source_mode == "csv" and request.snapshot is None:
        assert request.csv_text is not None
        return parse_csv_event_log(request.csv_text)
    assert request.snapshot is not None
    return minimize_snapshot(request.snapshot)


def construct_baseline(
    request: BaselineConstructRequest,
) -> tuple[CalibrationArtifact | None, dict[str, Any]]:
    extra: dict[str, Any] = {"sourceMode": request.source_mode, "contractVersion": "cg7.v1"}
    if request.source_mode == "synthetic":
        assert request.fixture_id is not None
        if request.fixture_id not in LABORATORY_FIXTURES:
            raise BaselineError(
                "unknown_fixture",
                "The fixture identifier is not in the synthetic catalog.",
            )
        snapshot = load_fixture(request.fixture_id, request.random_seed)
        engine_request = request_for_fixture(
            request.fixture_id, snapshot, approve=request.approve_lab_assumptions
        )
        artifact = calibrate(snapshot, engine_request)
        extra.update(
            {
                "fixtureId": request.fixture_id,
                "synthetic": True,
                "evidenceClass": "synthetic",
                "historicallyValidated": False,
                "disclosure": "Synthetic laboratory calibration. Not this Jira project's history.",
            }
        )
        return artifact, extra
    if request.source_mode == "manual":
        assert request.manual is not None
        artifact = construct_manual_artifact(request.manual)
        extra.update(
            {
                "fixtureId": None,
                "synthetic": False,
                "evidenceClass": "user_defined_exploratory",
                "historicallyValidated": False,
                "disclosure": "User-defined exploratory model. Not historically calibrated.",
                "manualSpec": request.manual.model_dump(by_alias=True),
            }
        )
        return artifact, extra
    snapshot = _source_snapshot(request)
    structural = validate_snapshot_structure(snapshot)
    if structural:
        raise BaselineError("invalid_evidence", structural)
    extra["suggestedMapping"] = suggest_status_mapping(snapshot)
    extra["snapshotFingerprint"] = snapshot.get("contentFingerprint")
    extra["synthetic"] = False
    extra["evidenceClass"] = (
        "csv_exploratory" if request.source_mode == "csv" else "source_linked_exploratory"
    )
    extra["historicallyValidated"] = False
    if request.calibration is None:
        extra.update(
            {
                "disclosure": "Review mapping and assumptions before constructing a source-linked model.",  # noqa: E501
                "snapshot": snapshot,
                "constructedModel": False,
            }
        )
        return None, extra
    artifact = calibrate(snapshot, request.calibration)
    extra.update(
        {
            "fixtureId": None,
            "disclosure": "Source-linked model. Importing records does not by itself establish historical validation.",  # noqa: E501
        }
    )
    extra["historicallyValidated"] = artifact.readiness_status == "validated_for_defined_scope"
    return artifact, extra


def reconstruct_from_claims(claims: dict[str, Any]) -> CalibrationArtifact:
    reconstruction = claims.get("reconstruction")
    if not isinstance(reconstruction, dict):
        raise BaselineError("invalid_baseline", "Baseline token is missing reconstruction claims.")
    request = BaselineConstructRequest.model_validate(reconstruction)
    artifact, extra = construct_baseline(request)
    if artifact is None:
        raise BaselineError(
            "baseline_not_executable", extra.get("disclosure") or "Baseline is not executable."
        )
    expected = claims.get("modelFingerprint")
    if expected and artifact.model_fingerprint != expected:
        raise BaselineError(
            "model_identity_violation",
            "Reconstructed baseline fingerprint does not match the signed baseline.",
        )
    return artifact
