from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import Field, model_validator

from app.calibration.construct import construct_model, model_fingerprint
from app.calibration.contracts import (
    ENGINE_VERSION,
    TEMPLATE_ID,
    AssumptionRecord,
    CalibrationArtifact,
    CalibrationDiagnostics,
    ExecutionMetadata,
    ParameterEstimate,
)
from app.calibration.snapshot import sha256_canonical
from app.domain.models import ContractModel

MANUAL_TEMPLATE_VERSION = "support-triage-resolution.manual.1"
MAX_VOLUME = 20_000
MAX_DAYS = 365
MIN_DAYS = 1


class ManualBaselineSpec(ContractModel):
    source_mode: Literal["manual"] = "manual"
    expected_volume: int = Field(ge=1, le=MAX_VOLUME)
    observation_days: int = Field(ge=MIN_DAYS, le=MAX_DAYS)
    operating_hours_per_day: float = Field(default=8, gt=0, le=24)
    triage_capacity: int = Field(ge=1, le=50)
    resolution_capacity: int = Field(ge=1, le=50)
    triage_mean_minutes: float = Field(gt=0, le=1_440)
    resolution_mean_minutes: float = Field(gt=0, le=2_880)
    triage_to_resolution_probability: float = Field(ge=0, le=1)
    sla_minutes: float = Field(default=240, gt=0, le=10_080)
    random_seed: int = Field(default=20_260_327, ge=0, le=2**63 - 1)

    @model_validator(mode="after")
    def finite_inputs(self) -> ManualBaselineSpec:
        for name in (
            "operating_hours_per_day",
            "triage_mean_minutes",
            "resolution_mean_minutes",
            "triage_to_resolution_probability",
            "sla_minutes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be a finite number")
        return self


def mean_interarrival_minutes(spec: ManualBaselineSpec) -> float:
    operating_minutes = spec.observation_days * spec.operating_hours_per_day * 60.0
    return operating_minutes / spec.expected_volume


def _estimate(
    parameter_id: str,
    path: str,
    value: float | int,
    unit: str,
    parameter_type: str,
) -> ParameterEstimate:
    return ParameterEstimate(
        parameter_id=parameter_id,
        target_model_path=path,
        parameter_type=parameter_type,
        value=value,
        unit=unit,
        estimation_method="user_specified",
        evidence_class="assumed",
        identifiability_status="assumption_required",
        sample_size=0,
        origin="approved_assumption",
        consumed_by_model=True,
        limitations=["User-defined exploratory parameter. Not historically calibrated."],
    )


def spec_fingerprint(spec: ManualBaselineSpec) -> str:
    return sha256_canonical(
        {"template": MANUAL_TEMPLATE_VERSION, "spec": spec.model_dump(by_alias=True)}
    )


def construct_manual_artifact(spec: ManualBaselineSpec) -> CalibrationArtifact:
    mean_ia = mean_interarrival_minutes(spec)
    if not math.isfinite(mean_ia) or mean_ia <= 0:
        raise ValueError("Computed interarrival time must be positive and finite.")
    estimates = [
        _estimate(
            "arrival.mean_interarrival_time",
            "sources[0].arrival.meanInterarrivalTime",
            mean_ia,
            "minutes",
            "rate",
        ),
        _estimate(
            "triage.processing_time.mean",
            "stages[triage].processingTime.mean",
            spec.triage_mean_minutes,
            "minutes",
            "duration",
        ),
        _estimate(
            "resolution.processing_time.mean",
            "stages[resolution].processingTime.mean",
            spec.resolution_mean_minutes,
            "minutes",
            "duration",
        ),
        _estimate(
            "resource.triage-team.capacity",
            "resourcePools[triage-team].capacity",
            spec.triage_capacity,
            "servers",
            "capacity",
        ),
        _estimate(
            "resource.resolution-team.capacity",
            "resourcePools[resolution-team].capacity",
            spec.resolution_capacity,
            "servers",
            "capacity",
        ),
        _estimate(
            "routing.triage_to_resolution",
            "routes[triage-success].options",
            spec.triage_to_resolution_probability,
            "probability",
            "routing",
        ),
    ]
    model = construct_model(estimates, spec.random_seed, sla_minutes=spec.sla_minutes)
    fingerprint = model_fingerprint(model)
    assumptions = [
        AssumptionRecord(
            assumption_id=item.parameter_id,
            affected_parameter=item.parameter_id,
            proposed_value=item.value if item.value is not None else 0,
            unit=item.unit,
            rationale="User-defined exploratory operation.",
            source="analyst",
            approval_status="approved",
            revision=1,
            limitations=item.limitations,
            evidence_available="none",
            operational_consequence="This value binds the executed model.",
        )
        for item in estimates
        if item.parameter_id != "arrival.mean_interarrival_time"
        and item.parameter_id != "routing.triage_to_resolution"
    ]
    provenance: dict[str, Any] = {
        "sourceMode": "manual",
        "evidenceClass": "user_defined_exploratory",
        "template": MANUAL_TEMPLATE_VERSION,
        "specFingerprint": spec_fingerprint(spec),
        "historicallyValidated": False,
    }
    return CalibrationArtifact(
        calibration_id=f"manual:{fingerprint[:16]}",
        source_snapshot_fingerprint=spec_fingerprint(spec),
        model_template_version=TEMPLATE_ID,
        mapping_version="status-role.1",
        parameter_estimates=estimates,
        assumptions=assumptions,
        constructed_model=model,
        model_fingerprint=fingerprint,
        training_configuration={"mode": "manual"},
        validation_configuration={"mode": "not_applicable"},
        diagnostics=CalibrationDiagnostics(notes=["Manual exploratory model. No historical holdout."]),  # noqa: E501
        readiness_status="model_constructed",
        provenance=provenance,
        execution_metadata=ExecutionMetadata(fixture_seed=spec.random_seed),
        validation_report=None,
        content_identity=sha256_canonical(
            {"spec": spec_fingerprint(spec), "model": fingerprint, "engine": ENGINE_VERSION}
        ),
    )
