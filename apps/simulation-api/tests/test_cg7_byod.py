from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.calibration.contracts import CalibrationRequest
from app.calibration.manual import ManualBaselineSpec, construct_manual_artifact, spec_fingerprint
from app.calibration.mapping import suggest_status_mapping
from app.calibration.snapshot import content_fingerprint, validate_snapshot_structure
from app.economics.decision import DecisionError, DecisionEvaluationRequest, evaluate_decision
from app.integrations.baselines import (
    BaselineConstructRequest,
    BaselineError,
    compact_reconstruction,
    construct_baseline,
)
from app.integrations.csv_events import CSV_TEMPLATE, CsvImportError, parse_csv_event_log
from app.integrations.evidence_token import (
    EvidenceTokenError,
    artifact_claims,
    bind_context,
    sign_claims,
    verify_claims,
)
from app.main import app

os.environ.setdefault("OPSTWIN_ALLOW_DEV_EVIDENCE_KEY", "1")

CSV = """case_id,activity,timestamp,work_duration_minutes,processing_stage
A,created,2026-01-01T08:00:00.000Z,,
A,triage_started,2026-01-01T08:05:00.000Z,6,triage
A,triage_completed,2026-01-01T08:12:00.000Z,,
A,resolution_started,2026-01-01T08:15:00.000Z,20,resolution
A,resolved,2026-01-01T08:40:00.000Z,,
B,created,2026-01-01T09:00:00.000Z,,
B,triage_started,2026-01-01T09:10:00.000Z,5,triage
B,resolved,2026-01-01T09:20:00.000Z,,
"""


def test_manual_specs_produce_distinct_fingerprints() -> None:
    light = ManualBaselineSpec(
        expected_volume=200,
        observation_days=30,
        triage_capacity=3,
        resolution_capacity=4,
        triage_mean_minutes=6,
        resolution_mean_minutes=12,
        triage_to_resolution_probability=0.5,
    )
    heavy = ManualBaselineSpec(
        expected_volume=800,
        observation_days=30,
        triage_capacity=1,
        resolution_capacity=1,
        triage_mean_minutes=12,
        resolution_mean_minutes=40,
        triage_to_resolution_probability=0.9,
    )
    left = construct_manual_artifact(light)
    right = construct_manual_artifact(heavy)
    assert left.model_fingerprint != right.model_fingerprint
    assert spec_fingerprint(light) != spec_fingerprint(heavy)
    assert left.provenance["evidenceClass"] == "user_defined_exploratory"
    assert left.constructed_model is not None
    assert left.constructed_model.sources[0].item_count == 1


def test_csv_template_normalizes_distinct_cases() -> None:
    snapshot = parse_csv_event_log(CSV)
    assert snapshot["schemaVersion"] == "os.1.0.0"
    assert len(snapshot["cases"]) == 2
    assert snapshot["contentFingerprint"]
    mutated = CSV.replace("A,resolved,2026-01-01T08:40:00.000Z,,", "A,resolved,2026-01-02T08:40:00.000Z,,")  # noqa: E501
    other = parse_csv_event_log(mutated)
    assert other["contentFingerprint"] != snapshot["contentFingerprint"]


def _assumption(parameter_id: str, value: float, unit: str) -> dict[str, object]:
    return {
        "assumptionId": parameter_id,
        "affectedParameter": parameter_id,
        "proposedValue": value,
        "unit": unit,
        "rationale": "Explicit analyst assumption.",
        "source": "analyst",
        "approvalStatus": "approved",
        "revision": 1,
        "limitations": ["Not inferred from status residence."],
        "evidenceAvailable": "none identifiable",
        "operationalConsequence": "Binds the executed exploratory model.",
    }


def _csv_calibration(snapshot: dict) -> CalibrationRequest:
    suggested = suggest_status_mapping(snapshot)
    return CalibrationRequest.model_validate(
        {
            "snapshotReference": snapshot["snapshotId"],
            "snapshotFingerprint": snapshot["contentFingerprint"],
            "operationalMapping": {
                "mappingVersion": "status-role.1",
                "reviewed": True,
                "statuses": [
                    {
                        "statusId": item["statusId"],
                        "role": item["role"],
                        "stageId": item["stageId"],
                        "reviewed": True,
                    }
                    for item in suggested["statuses"]
                ],
            },
            "assumptionSet": [
                _assumption("arrival.mean_interarrival_time", 60, "minutes"),
                _assumption("triage.processing_time.mean", 8, "minutes"),
                _assumption("resolution.processing_time.mean", 20, "minutes"),
                _assumption("resource.triage-team.capacity", 2, "servers"),
                _assumption("resource.resolution-team.capacity", 3, "servers"),
            ],
            "estimationConfiguration": {
                "treatWorklogsAsProcessing": False,
                "allowAssumptionBasedModel": True,
            },
        }
    )


def test_csv_template_is_canonical_and_drives_construction() -> None:
    snapshot = parse_csv_event_log(CSV_TEMPLATE)
    assert validate_snapshot_structure(snapshot) is None
    assert snapshot["completenessStatus"] == "partial"
    assert snapshot["sourceProject"]["key"] == "CSV"
    suggested = suggest_status_mapping(snapshot)
    resolution = next(item for item in suggested["statuses"] if item["statusId"] == "s-res")
    assert resolution["role"] == "processing"
    assert resolution["stageId"] == "resolution"
    artifact, extra = construct_baseline(
        BaselineConstructRequest(
            source_mode="csv",
            csv_text=CSV_TEMPLATE,
            calibration=_csv_calibration(snapshot),
        )
    )
    assert artifact is not None
    assert artifact.constructed_model is not None
    assert extra["sourceMode"] == "csv"
    reconstruction = compact_reconstruction(artifact, BaselineConstructRequest(source_mode="csv", csv_text=CSV_TEMPLATE))  # noqa: E501
    assert "snapshot" not in reconstruction
    assert len(__import__("json").dumps(reconstruction).encode()) < 20_000


def test_independent_csv_is_valid_and_malformed_csv_is_refused() -> None:
    other = """case_id,activity,timestamp
TICKET-9,created,2026-02-01T10:00:00.000Z
TICKET-9,triage_started,2026-02-01T10:05:00.000Z
TICKET-9,resolution_started,2026-02-01T10:20:00.000Z
TICKET-9,resolved,2026-02-01T11:00:00.000Z
"""
    snapshot = parse_csv_event_log(other)
    assert validate_snapshot_structure(snapshot) is None
    assert snapshot["cases"][0]["caseId"] == "TICKET-9"
    with pytest.raises(CsvImportError):
        parse_csv_event_log("not,a,csv\n1,2,3")
    with pytest.raises(CsvImportError):
        parse_csv_event_log("case_id,activity,timestamp\nX,created,not-a-date")


def test_browser_jira_snapshot_is_not_trusted_evidence() -> None:
    snapshot = parse_csv_event_log(CSV_TEMPLATE)
    snapshot["sourceSystem"] = "jira-jsm"
    snapshot["sourceProject"] = {
        "reference": "project:OPS",
        "key": "OPS",
        "name": "Ops",
        "serviceDeskId": None,
    }
    snapshot["provenance"]["evidenceClass"] = "observed"
    snapshot["provenance"]["transportAuthenticity"] = "unknown"
    with pytest.raises(BaselineError, match="trusted Forge resolver"):
        construct_baseline(
            BaselineConstructRequest(
                source_mode="jira",
                snapshot=snapshot,
                trusted_extraction=False,
            )
        )
    with pytest.raises(BaselineError, match="live authorized extraction"):
        construct_baseline(
            BaselineConstructRequest(
                source_mode="jira",
                snapshot=snapshot,
                trusted_extraction=True,
                authorized_project_key="OPS",
            )
        )


def test_signed_artifacts_bind_project_principal_and_purpose() -> None:
    token = sign_claims(
        artifact_claims(
            kind="baseline",
            purpose="transform",
            app_id="app",
            installation_id="inst",
            environment_type="DEVELOPMENT",
            project_key="OPS",
            principal_id="user-1",
            extra={"modelFingerprint": "a" * 64},
        )
    )
    claims = verify_claims(token)
    bind_context(
        claims,
        app_id="app",
        installation_id="inst",
        environment_type="DEVELOPMENT",
        project_key="OPS",
        principal_id="user-1",
        kind="baseline",
        purpose="transform",
    )
    with pytest.raises(EvidenceTokenError, match="projects"):
        bind_context(
            claims,
            app_id="app",
            installation_id="inst",
            environment_type="DEVELOPMENT",
            project_key="OTHER",
            principal_id="user-1",
        )
    with pytest.raises(EvidenceTokenError, match="principal"):
        bind_context(
            claims,
            app_id="app",
            installation_id="inst",
            environment_type="DEVELOPMENT",
            project_key="OPS",
            principal_id="user-2",
        )
    with pytest.raises(EvidenceTokenError, match="artifact type"):
        bind_context(
            claims,
            app_id="app",
            installation_id="inst",
            environment_type="DEVELOPMENT",
            project_key="OPS",
            principal_id="user-1",
            kind="experiment",
        )


def test_signed_evidence_rejects_tampering() -> None:
    token = sign_claims(
        artifact_claims(
            kind="experiment",
            purpose="evaluate",
            app_id="app",
            installation_id="inst",
            environment_type="DEVELOPMENT",
            project_key="OPS",
            principal_id="user-1",
            extra={"evidence": {"n": 1}},
        )
    )
    claims = verify_claims(token)
    assert claims["evidence"]["n"] == 1
    head, body, digest = token.split(".")
    tampered = f"{head}.{body[:-2]}ab.{digest}"
    with pytest.raises(Exception, match="signature|malformed"):
        verify_claims(tampered)


def test_capacity_break_even_cannot_use_ai_subscription() -> None:
    from app.domain.decision import DecisionAssumptions
    from app.interventions.catalog import (
        CapacityIntervention,
        ExperimentExecution,
        NamedAlternative,
    )
    from app.interventions.execute import AlternativeEvidence, MultiExperimentEvidence, PackedMetric
    from app.interventions.identity import operational_experiment_identity

    alternatives = [
        NamedAlternative(
            alternative_id="human-expansion",
            intervention=CapacityIntervention(extra_triage_capacity=0, extra_resolution_capacity=1),
        )
    ]
    execution = ExperimentExecution(item_count=20, run_count=2, base_seed=20261127)
    fingerprint = "c" * 64
    identity = operational_experiment_identity(
        fixture_id="cg5-hybrid-support",
        model_fingerprint=fingerprint,
        alternatives=alternatives,
        execution=execution,
    )
    packed = PackedMetric(mean=10, p50=10, lower=10, upper=10, unit="minutes")
    evidence = MultiExperimentEvidence(
        fixture_id="cg5-hybrid-support",
        experiment_id="lab",
        experiment_identity=identity,
        experiment_status="complete",
        approximations=[],
        baseline_readiness="model_constructed",
        baseline_class="constructed_exploratory",
        historically_adequate=False,
        exploratory=True,
        disclosures=[],
        baseline_inventory={},
        calibrated_model_fingerprint=fingerprint,
        executed_model_fingerprint=fingerprint,
        identities_agree=True,
        experiment=execution,
        baseline_metrics={"averageCycleTime": packed, "completedItems": PackedMetric(mean=20, unit="items")},  # noqa: E501
        alternatives=[
            AlternativeEvidence(
                alternative_id="human-expansion",
                intervention_kind="capacity",
                intervention_name="capacity",
                status="valid",
                system_metrics={"averageCycleTime": packed, "completedItems": PackedMetric(mean=20, unit="items")},  # noqa: E501
            )
        ],
        integrity_status="passed",
        improvement_interpretation="paired",
    )
    with pytest.raises(DecisionError, match="does not use AI"):
        evaluate_decision(
            DecisionEvaluationRequest(
                fixture_id="cg5-hybrid-support",
                alternatives=alternatives,
                execution=execution,
                experiment_identity=identity,
                evidence=evidence,
                assumptions=DecisionAssumptions(evaluation_basis="recurring_period", expected_demand_per_month=20),  # noqa: E501
                explore={
                    "strategyId": "human-expansion",
                    "parameter": "aiSubscriptionMonthly",
                    "low": 0,
                    "high": 100,
                    "pointCount": 3,
                },
            )
        )


def test_construct_baseline_requires_fit() -> None:
    response = TestClient(app).post(
        "/api/integrations/atlassian/v1/construct-baseline",
        json={"contractVersion": "cg7.v1", "sourceMode": "manual"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "FIT_INVALID"


def _jira_snapshot_from_csv() -> dict:
    snapshot = parse_csv_event_log(CSV_TEMPLATE)
    snapshot["sourceSystem"] = "jira-jsm"
    snapshot["sourceProject"] = {
        "reference": "project:OPS",
        "key": "OPS",
        "name": "Ops",
        "serviceDeskId": None,
    }
    snapshot["provenance"]["evidenceClass"] = "observed"
    snapshot["provenance"]["transportAuthenticity"] = "live_api"
    snapshot["provenance"]["sourceProject"] = "project:OPS"
    for case in snapshot["cases"]:
        case["syntheticOrigin"] = True
        case["projectReference"] = "project:OPS"
        case["sourceSystem"] = "jira-jsm"
    snapshot["contentFingerprint"] = content_fingerprint(snapshot)
    return snapshot


def test_changed_source_fingerprint_requires_review() -> None:
    preview, extra = construct_baseline(
        BaselineConstructRequest(
            source_mode="jira",
            snapshot=_jira_snapshot_from_csv(),
            trusted_extraction=True,
            authorized_project_key="OPS",
        )
    )
    assert preview is None
    reviewed = extra["snapshot"]
    calibration = _csv_calibration(reviewed).model_copy(update={"snapshot_fingerprint": "a" * 64})
    with pytest.raises(BaselineError, match="changed after the reviewed"):
        construct_baseline(
            BaselineConstructRequest(
                source_mode="jira",
                snapshot=reviewed,
                trusted_extraction=True,
                authorized_project_key="OPS",
                calibration=calibration,
            )
        )


def test_jira_hosted_synthetic_origin_is_preserved() -> None:
    preview, extra = construct_baseline(
        BaselineConstructRequest(
            source_mode="jira",
            snapshot=_jira_snapshot_from_csv(),
            trusted_extraction=True,
            authorized_project_key="OPS",
        )
    )
    assert preview is None
    reviewed = extra["snapshot"]
    artifact, built = construct_baseline(
        BaselineConstructRequest(
            source_mode="jira",
            snapshot=reviewed,
            trusted_extraction=True,
            authorized_project_key="OPS",
            calibration=_csv_calibration(reviewed),
        )
    )
    assert artifact is not None
    assert built["synthetic"] is True
    assert built["evidenceClass"] == "synthetic"
    assert artifact.provenance["evidenceClass"] == "synthetic"
    assert built["snapshotFingerprint"] == reviewed["contentFingerprint"]


def test_csv_template_completes_simulation_and_economics() -> None:
    from app.domain.decision import DecisionAssumptions
    from app.interventions.catalog import (
        AssistedIntervention,
        CapacityIntervention,
        ExperimentExecution,
        NamedAlternative,
    )
    from app.interventions.execute import run_multi_intervention_experiment

    snapshot = parse_csv_event_log(CSV_TEMPLATE)
    artifact, extra = construct_baseline(
        BaselineConstructRequest(
            source_mode="csv",
            csv_text=CSV_TEMPLATE,
            calibration=_csv_calibration(snapshot),
        )
    )
    assert artifact is not None
    assert artifact.constructed_model is not None
    alternatives = [
        NamedAlternative(
            alternative_id="human-expansion",
            intervention=CapacityIntervention(extra_triage_capacity=0, extra_resolution_capacity=1),
        ),
        NamedAlternative(
            alternative_id="ai-assisted",
            intervention=AssistedIntervention(
                stage_id="triage",
                coverage=0.5,
                processing_reduction=0.4,
                review_overhead_minutes=0.25,
            ),
        ),
    ]
    execution = ExperimentExecution(item_count=20, run_count=2, base_seed=20261127)
    evidence = run_multi_intervention_experiment(
        artifact,
        alternatives,
        execution,
        experiment_id="csv-complete",
        source_mode="csv",
        synthetic=False,
    )
    assert evidence.experiment_status == "complete"
    assert evidence.identities_agree is True
    assert evidence.source_mode == "csv"
    assert evidence.synthetic is False
    result = evaluate_decision(
        DecisionEvaluationRequest(
            alternatives=alternatives,
            execution=execution,
            experiment_identity=evidence.experiment_identity,
            evidence=evidence,
            assumptions=DecisionAssumptions(
                origin="csv_exploratory",
                evaluation_basis="fixed_workload",
                realization_mechanism="none",
            ),
        )
    )
    assert result.integrity_status == "passed"
    assert result.synthetic is False
    assert extra["sourceMode"] == "csv"


def test_shared_principal_and_missing_principal_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.integrations import remote_baseline
    from app.integrations.fit import REGISTERED_APP_ID

    installation = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"
    monkeypatch.setattr(
        remote_baseline,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {"installationId": installation, "payload": {}},
    )
    client = TestClient(app)
    missing = client.post(
        "/api/integrations/atlassian/v1/construct-baseline",
        json={
            "contractVersion": "cg7.v1",
            "sourceMode": "synthetic",
            "fixtureId": "cg3-golden-analytical",
            "authorizedProjectKey": "OPS",
        },
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "SCOPE_MISMATCH"
    shared = client.post(
        "/api/integrations/atlassian/v1/construct-baseline",
        json={
            "contractVersion": "cg7.v1",
            "sourceMode": "synthetic",
            "fixtureId": "cg3-golden-analytical",
            "authorizedProjectKey": "OPS",
            "authorizedPrincipal": "scope:installation-user-context",
        },
    )
    assert shared.status_code == 422
    monkeypatch.setattr(
        remote_baseline,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {
            "installationId": installation,
            "payload": {"principal": {"accountId": "user-real"}},
        },
    )
    mismatched = client.post(
        "/api/integrations/atlassian/v1/construct-baseline",
        json={
            "contractVersion": "cg7.v1",
            "sourceMode": "synthetic",
            "fixtureId": "cg3-golden-analytical",
            "authorizedProjectKey": "OPS",
            "authorizedPrincipal": "user-1",
        },
    )
    assert mismatched.status_code == 422
    assert REGISTERED_APP_ID


def test_transform_rejects_inconsistent_source_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.integrations import remote_transform
    from app.integrations.fit import REGISTERED_APP_ID

    installation = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"
    monkeypatch.setattr(
        remote_transform,
        "verify_forge_invocation_token",
        lambda *_args, **_kwargs: {"installationId": installation, "payload": {}},
    )
    token = sign_claims(
        artifact_claims(
            kind="baseline",
            purpose="transform",
            app_id=REGISTERED_APP_ID,
            installation_id=installation,
            environment_type="DEVELOPMENT",
            project_key="OPS",
            principal_id="user-1",
            extra={"sourceMode": "jira", "synthetic": True, "modelFingerprint": "a" * 64},
        )
    )
    response = TestClient(app).post(
        "/api/integrations/atlassian/v1/transform",
        json={
            "contractVersion": "cg5.v1",
            "sourceMode": "csv",
            "baselineToken": token,
            "alternatives": [
                {
                    "alternativeId": "human-expansion",
                    "intervention": {
                        "kind": "capacity",
                        "extraTriageCapacity": 0,
                        "extraResolutionCapacity": 1,
                    },
                }
            ],
            "execution": {"itemCount": 20, "runCount": 2, "baseSeed": 20261127},
            "authorizedProjectKey": "OPS",
            "authorizedPrincipal": "user-1",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SCOPE_MISMATCH"
