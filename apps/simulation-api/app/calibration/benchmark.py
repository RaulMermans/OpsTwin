from __future__ import annotations

import time
from typing import Any

from app.calibration.catalog import FIXTURE_IDS, load_fixture, request_for_fixture
from app.calibration.contracts import CalibrationArtifact, CalibrationRequest
from app.calibration.histories import ground_truth
from app.calibration.workflow import calibrate


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
                    "rationale": "Uncalibrated default template.",
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
                    "rationale": "Uncalibrated default template.",
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
                    "rationale": "Uncalibrated default template.",
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
                    "rationale": "Uncalibrated default template.",
                    "source": "naive-baseline",
                    "approvalStatus": "approved",
                    "revision": 1,
                    "evidenceAvailable": "none",
                    "operationalConsequence": "Default is not evidence.",
                },
            ],
            "estimationConfiguration": {"treatWorklogsAsProcessing": False, "allowAssumptionBasedModel": True},  # noqa: E501
            "randomSeed": artifact_seed,
        }
    )
    # Force a dummy arrival assumption by injecting a proposed interarrival via a patched snapshot path:  # noqa: E501
    artifact = calibrate(snapshot, request)
    return artifact


def evaluate_profile(fixture_id: str, seed: int) -> dict[str, Any]:
    profile = FIXTURE_IDS[fixture_id]
    snapshot = load_fixture(fixture_id, seed)
    truth = ground_truth(profile)
    approve = profile not in {"golden", "observable"}
    if profile in {"golden", "observable"}:
        approve = True
    request = request_for_fixture(fixture_id, snapshot, approve=approve)
    started = time.perf_counter()
    artifact = calibrate(snapshot, request)
    runtime_ms = (time.perf_counter() - started) * 1000
    arrival = _estimate_value(artifact, "arrival.mean_interarrival_time")
    truth_ia = truth.get("arrival_mean_interarrival")
    arrival_error = None
    if arrival is not None and isinstance(truth_ia, int | float):
        arrival_error = abs(arrival - float(truth_ia)) / float(truth_ia)
    refused_service = any(
        item.parameter_id.endswith("processing_time.mean")
        and item.identifiability_status in {"not_identifiable", "insufficient_evidence"}
        and item.estimation_method.startswith("refused")
        for item in artifact.parameter_estimates
    )
    return {
        "fixtureId": fixture_id,
        "profile": profile,
        "seed": seed,
        "readiness": artifact.readiness_status,
        "failureClass": artifact.failure_class,
        "arrivalEstimate": arrival,
        "arrivalTruth": truth_ia,
        "arrivalRelativeError": arrival_error,
        "identifiabilityArrival": next(
            (
                item.identifiability_status
                for item in artifact.parameter_estimates
                if item.parameter_id == "arrival.mean_interarrival_time"
            ),
            None,
        ),
        "validationOutcome": artifact.validation_report.overall_outcome if artifact.validation_report else None,  # noqa: E501
        "runtimeMs": runtime_ms,
        "refusedUnsupportedService": refused_service,
        "modelFingerprint": artifact.model_fingerprint,
    }


def run_suite(seeds: tuple[int, ...] = (1, 2, 3)) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fixture_id in FIXTURE_IDS:
        for seed in seeds:
            rows.append(evaluate_profile(fixture_id, seed))
    return rows


if __name__ == "__main__":
    import json
    import sys

    selected = (21,) if "--smoke" in sys.argv else (1, 2, 3)
    print(json.dumps(run_suite(selected), indent=2))
