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
    trusted_extraction: bool = False
    authorized_project_key: str | None = None
    authorized_principal: str | None = None

    @model_validator(mode="after")
    def matching_source(self) -> BaselineConstructRequest:
        if self.source_mode == "synthetic" and not self.fixture_id:
            raise ValueError("synthetic baselines require fixtureId")
        if self.source_mode == "manual" and self.manual is None:
            raise ValueError("manual baselines require a parameter specification")
        if self.source_mode == "jira" and self.snapshot is None:
            raise ValueError("Jira baselines require a trusted operational snapshot")
        if self.source_mode == "csv" and self.csv_text is None:
            raise ValueError("CSV baselines require csvText")
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
        "schemaVersion",
        "caseId",
        "sourceReference",
        "sourceSystem",
        "projectReference",
        "requestTypeReference",
        "priorityReference",
        "currentStatusReference",
        "createdAt",
        "resolvedAt",
        "createdAtInvalid",
        "observationStatus",
        "lifecycleCompleteness",
        "assigneeReference",
        "updatedAt",
        "syntheticOrigin",
        "originUnknown",
        "reopened",
        "provenance",
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
    if request.source_mode == "csv":
        assert request.csv_text is not None
        return parse_csv_event_log(request.csv_text)
    if request.source_mode == "jira" and not request.trusted_extraction:
        raise BaselineError(
            "untrusted_evidence",
            "Jira evidence must be extracted by the trusted Forge resolver, not supplied from the browser.",  # noqa: E501
        )
    assert request.snapshot is not None
    snapshot = minimize_snapshot(request.snapshot)
    project = (snapshot.get("sourceProject") or {}).get("key")
    if (
        request.authorized_project_key
        and project
        and project != request.authorized_project_key
    ):
        raise BaselineError(
            "untrusted_project",
            "The extracted snapshot does not belong to the authorized project.",
        )
    provenance = snapshot.get("provenance") or {}
    if provenance.get("evidenceClass") == "observed" and provenance.get("transportAuthenticity") != "live_api":  # noqa: E501
        raise BaselineError(
            "untrusted_evidence",
            "Observed Jira records require live authorized extraction.",
        )
    return snapshot


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
    cases = snapshot.get("cases") or []
    if request.source_mode == "jira" and cases and all(item.get("syntheticOrigin") for item in cases):  # noqa: E501
        extra["synthetic"] = True
        extra["evidenceClass"] = "synthetic"
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
    computed = snapshot.get("contentFingerprint")
    reviewed = request.calibration.snapshot_fingerprint
    if computed != reviewed:
        raise BaselineError(
            "review_required",
            "Authorized source records changed after the reviewed snapshot. Re-import and review mapping again.",  # noqa: E501
        )
    artifact = calibrate(snapshot, request.calibration)
    extra.update(
        {
            "fixtureId": None,
            "disclosure": (
                "Jira-hosted synthetic laboratory records. Not genuine historical operations."
                if extra["evidenceClass"] == "synthetic"
                else "Source-linked model. Importing records does not by itself establish historical validation."  # noqa: E501
            ),
        }
    )
    extra["historicallyValidated"] = artifact.readiness_status == "validated_for_defined_scope"
    extra.pop("snapshot", None)
    if extra["evidenceClass"] == "synthetic":
        provenance = dict(artifact.provenance or {})
        provenance["evidenceClass"] = "synthetic"
        artifact = artifact.model_copy(update={"provenance": provenance})
    return artifact, extra


def compact_reconstruction(
    artifact: CalibrationArtifact, request: BaselineConstructRequest
) -> dict[str, Any]:
    if request.source_mode == "synthetic":
        return {
            "contractVersion": "cg7.v1",
            "sourceMode": "synthetic",
            "fixtureId": request.fixture_id,
            "approveLabAssumptions": request.approve_lab_assumptions,
            "randomSeed": request.random_seed,
        }
    if request.source_mode == "manual":
        assert request.manual is not None
        return {
            "contractVersion": "cg7.v1",
            "sourceMode": "manual",
            "manual": request.manual.model_dump(by_alias=True, exclude_none=True),
        }
    payload = artifact.model_dump(by_alias=True, exclude_none=True)
    payload.pop("validationReport", None)
    return {"sourceMode": request.source_mode, "artifact": payload}


def reconstruct_from_claims(claims: dict[str, Any]) -> CalibrationArtifact:
    reconstruction = claims.get("reconstruction")
    if not isinstance(reconstruction, dict):
        raise BaselineError("invalid_baseline", "Baseline token is missing reconstruction claims.")
    signed = reconstruction.get("artifact")
    if isinstance(signed, dict):
        artifact = CalibrationArtifact.model_validate(signed)
        expected = claims.get("modelFingerprint")
        if expected and artifact.model_fingerprint != expected:
            raise BaselineError(
                "model_identity_violation",
                "Reconstructed baseline fingerprint does not match the signed baseline.",
            )
        return artifact
    request = BaselineConstructRequest.model_validate(reconstruction)
    rebuilt, extra = construct_baseline(request)
    if rebuilt is None:
        raise BaselineError(
            "baseline_not_executable", extra.get("disclosure") or "Baseline is not executable."
        )
    expected = claims.get("modelFingerprint")
    if expected and rebuilt.model_fingerprint != expected:
        raise BaselineError(
            "model_identity_violation",
            "Reconstructed baseline fingerprint does not match the signed baseline.",
        )
    return rebuilt
