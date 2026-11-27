from __future__ import annotations

import time
from typing import Any

from app.calibration.catalog import FIXTURE_IDS, load_fixture, request_for_fixture
from app.calibration.contracts import CalibrationArtifact, CalibrationRequest
from app.calibration.histories import ground_truth
from app.calibration.workflow import calibrate

PROFILE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "golden": {
        "must_construct": True,
        "must_refuse": False,
        "arrival_recovery": True,
        "service_recovery": True,
        "routing_recovery": True,
        "false_confidence_if_validated": False,
        "historical_adequacy": "not_required_for_parameter_recovery",
    },
    "observable": {
        "must_construct": True,
        "must_refuse": False,
        "arrival_recovery": True,
        "service_recovery": True,
        "routing_recovery": True,
        "false_confidence_if_validated": False,
    },
    "partial": {
        "must_construct": True,
        "must_refuse": False,
        "arrival_recovery": True,
        "service_recovery": False,
        "routing_recovery": True,
        "false_confidence_if_validated": False,
    },
    "noisy": {
        "must_construct": False,
        "must_refuse": True,
        "failure": ["insufficient_evidence"],
        "false_confidence_if_validated": True,
    },
    "nonstationary": {
        "must_construct": False,
        "must_refuse": True,
        "failure": ["statistical_estimation_failure"],
        "false_confidence_if_validated": True,
    },
    "misspecified": {
        "must_construct": False,
        "must_refuse": True,
        "failure": ["unsupported_topology"],
        "false_confidence_if_validated": True,
    },
    "mixed": {
        "must_construct": True,
        "must_refuse": False,
        "arrival_recovery": True,
        "service_recovery": False,
        "false_confidence_if_validated": False,
    },
    "shift": {
        "must_construct": True,
        "must_refuse": False,
        "arrival_recovery": True,
        "temporal_shift": True,
        "false_confidence_if_validated": True,
    },
}

ARRIVAL_RELATIVE_TOLERANCE = 0.25


def _estimate_value(artifact: CalibrationArtifact, parameter_id: str) -> float | None:
    match = next((item for item in artifact.parameter_estimates if item.parameter_id == parameter_id), None)  # noqa: E501
    if match is None or not isinstance(match.value, int | float):
        return None
    return float(match.value)


def naive_baseline(snapshot: dict[str, Any], artifact_seed: int) -> CalibrationArtifact:
    request = CalibrationRequest.model_validate(
        {
            "snapshotReference": "naive",
            "snapshotFingerprint": snapshot["contentFingerprint"],
            "operationalMapping": {
                "reviewed": True,
                "statuses": [
                    {"statusId": "s-open", "role": "queue", "reviewed": True},
                    {"statusId": "s-triage", "role": "processing", "stageId": "triage", "reviewed": True},  # noqa: E501
                    {"statusId": "s-res", "role": "processing", "stageId": "resolution", "reviewed": True},  # noqa: E501
                    {"statusId": "s-done", "role": "completed", "reviewed": True},
                ],
            },
            "assumptionSet": [
                {
                    "assumptionId": "triage.processing_time.mean",
                    "affectedParameter": "triage.processing_time.mean",
                    "proposedValue": 30,
                    "unit": "minutes",
                    "rationale": "Default service assumption with estimated arrivals.",
                    "source": "naive-baseline",
                    "approvalStatus": "approved",
                    "revision": 1,
                    "evidenceAvailable": "none",
                    "operationalConsequence": "Default is not evidence.",
                },
                {
                    "assumptionId": "resolution.processing_time.mean",
                    "affectedParameter": "resolution.processing_time.mean",
                    "proposedValue": 30,
                    "unit": "minutes",
                    "rationale": "Default service assumption with estimated arrivals.",
                    "source": "naive-baseline",
                    "approvalStatus": "approved",
                    "revision": 1,
                    "evidenceAvailable": "none",
                    "operationalConsequence": "Default is not evidence.",
                },
                {
                    "assumptionId": "resource.triage-team.capacity",
                    "affectedParameter": "resource.triage-team.capacity",
                    "proposedValue": 1,
                    "unit": "servers",
                    "rationale": "Default capacity assumption with estimated arrivals.",
                    "source": "naive-baseline",
                    "approvalStatus": "approved",
                    "revision": 1,
                    "evidenceAvailable": "none",
                    "operationalConsequence": "Default is not evidence.",
                },
                {
                    "assumptionId": "resource.resolution-team.capacity",
                    "affectedParameter": "resource.resolution-team.capacity",
                    "proposedValue": 1,
                    "unit": "servers",
                    "rationale": "Default capacity assumption with estimated arrivals.",
                    "source": "naive-baseline",
                    "approvalStatus": "approved",
                    "revision": 1,
                    "evidenceAvailable": "none",
                    "operationalConsequence": "Default is not evidence.",
                },
            ],
            "estimationConfiguration": {"treatWorklogsAsProcessing": False, "allowAssumptionBasedModel": True},  # noqa: E501
            "executionBudget": {"maxReplications": 3, "maxItems": 200},
            "randomSeed": artifact_seed,
        }
    )
    return calibrate(snapshot, request)


def _score_row(artifact: CalibrationArtifact, fixture_id: str, seed: int, runtime_ms: float) -> dict[str, Any]:  # noqa: E501
    profile = FIXTURE_IDS[fixture_id]
    truth = ground_truth(profile)
    arrival = _estimate_value(artifact, "arrival.mean_interarrival_time")
    triage = _estimate_value(artifact, "triage.processing_time.mean")
    routing = _estimate_value(artifact, "routing.triage_to_resolution")
    truth_ia = truth.get("arrival_mean_interarrival")
    arrival_error = None
    if arrival is not None and isinstance(truth_ia, int | float):
        arrival_error = abs(arrival - float(truth_ia)) / float(truth_ia)
    service_error = None
    if triage is not None and artifact.parameter_estimates:
        triage_est = next(item for item in artifact.parameter_estimates if item.parameter_id == "triage.processing_time.mean")  # noqa: E501
        if triage_est.origin == "empirical_estimate" and isinstance(truth.get("triage_mean"), int | float):  # noqa: E501
            service_error = abs(triage - float(truth["triage_mean"])) / float(truth["triage_mean"])
    refused_service = any(
        item.parameter_id.endswith("processing_time.mean")
        and item.identifiability_status in {"not_identifiable", "insufficient_evidence"}
        and item.estimation_method.startswith("refused")
        for item in artifact.parameter_estimates
    )
    expectation = PROFILE_EXPECTATIONS[profile]
    validated = artifact.readiness_status == "validated_for_defined_scope"
    false_confidence = bool(expectation.get("false_confidence_if_validated")) and validated
    arrival_ok = True
    if expectation.get("arrival_recovery"):
        arrival_ok = arrival_error is not None and arrival_error < ARRIVAL_RELATIVE_TOLERANCE
    refuse_ok = True
    if expectation.get("must_refuse"):
        refuse_ok = artifact.failure_class in set(expectation.get("failure") or [])  # noqa: E501
    construct_ok = (artifact.constructed_model is not None) == bool(expectation.get("must_construct")) or expectation.get("must_refuse")  # noqa: E501
    if expectation.get("must_refuse"):
        construct_ok = artifact.constructed_model is None
    return {
        "fixtureId": fixture_id,
        "profile": profile,
        "fixtureSeed": seed,
        "simulationSeeds": artifact.execution_metadata.simulation_seeds,
        "readiness": artifact.readiness_status,
        "failureClass": artifact.failure_class,
        "arrivalEstimate": arrival,
        "arrivalTruth": truth_ia,
        "arrivalRelativeError": arrival_error,
        "serviceRelativeError": service_error,
        "routingEstimate": routing,
        "identifiabilityArrival": next(
            (
                item.identifiability_status
                for item in artifact.parameter_estimates
                if item.parameter_id == "arrival.mean_interarrival_time"
            ),
            None,
        ),
        "validationOutcome": artifact.validation_report.overall_outcome if artifact.validation_report else None,  # noqa: E501
        "validationClass": artifact.validation_report.validation_class if artifact.validation_report else None,  # noqa: E501
        "runtimeMs": runtime_ms,
        "refusedUnsupportedService": refused_service,
        "modelFingerprint": artifact.model_fingerprint,
        "executionIdentity": artifact.execution_identity,
        "falseConfidence": false_confidence,
        "arrivalRecovered": arrival_ok,
        "refusalCorrect": refuse_ok,
        "constructionCorrect": construct_ok,
        "replicationCount": artifact.execution_metadata.replication_count,
    }


def evaluate_profile(fixture_id: str, seed: int) -> dict[str, Any]:
    snapshot = load_fixture(fixture_id, seed)
    profile = FIXTURE_IDS[fixture_id]
    request = request_for_fixture(fixture_id, snapshot, approve=True)
    started = time.perf_counter()
    artifact = calibrate(snapshot, request)
    runtime_ms = (time.perf_counter() - started) * 1000
    row = _score_row(artifact, fixture_id, seed, runtime_ms)
    if artifact.constructed_model is not None:
        naive = naive_baseline(snapshot, seed)
        row["naiveLabel"] = "estimated_arrivals_default_service_capacity"
        row["naiveReadiness"] = naive.readiness_status
        row["naiveValidationOutcome"] = (
            naive.validation_report.overall_outcome if naive.validation_report else None
        )
        calibrated_arrival = artifact.validation_report.targets[0].relative_error if artifact.validation_report else None  # noqa: E501
        naive_arrival = naive.validation_report.targets[0].relative_error if naive.validation_report else None  # noqa: E501
        row["calibratedArrivalHoldoutError"] = calibrated_arrival
        row["naiveArrivalHoldoutError"] = naive_arrival
    else:
        row["naiveLabel"] = None
    row["profileIntent"] = PROFILE_EXPECTATIONS[profile]
    return row


def run_suite(seeds: tuple[int, ...] = (1, 2, 3)) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fixture_id in FIXTURE_IDS:
        for seed in seeds:
            rows.append(evaluate_profile(fixture_id, seed))
    return rows


def suite_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    false_confidence = sum(1 for row in rows if row.get("falseConfidence"))
    refusals = sum(1 for row in rows if row.get("refusalCorrect") is False)
    return {
        "rows": len(rows),
        "falseConfidenceCount": false_confidence,
        "falseConfidenceRate": false_confidence / len(rows) if rows else None,
        "incorrectRefusalCount": refusals,
        "meanRuntimeMs": sum(row["runtimeMs"] for row in rows) / len(rows) if rows else None,
        "passConstruction": sum(1 for row in rows if row.get("constructionCorrect")),
    }


if __name__ == "__main__":
    import json
    import sys

    selected = (21,) if "--smoke" in sys.argv else (1, 2, 3)
    rows = run_suite(selected)
    print(json.dumps({"rows": rows, "summary": suite_summary(rows)}, indent=2))
