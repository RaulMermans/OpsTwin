from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.calibration.manual import ManualBaselineSpec, construct_manual_artifact, spec_fingerprint
from app.economics.decision import DecisionError, DecisionEvaluationRequest, evaluate_decision
from app.integrations.csv_events import parse_csv_event_log
from app.integrations.evidence_token import sign_claims, verify_claims
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


def test_signed_evidence_rejects_tampering() -> None:
    token = sign_claims({"kind": "experiment", "appId": "app", "installationId": "inst", "environmentType": "DEVELOPMENT", "evidence": {"n": 1}})  # noqa: E501
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
