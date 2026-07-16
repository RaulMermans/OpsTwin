from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from app.domain.comparison import ScenarioOverride
from app.domain.models import OperationalModel
from app.domain.sensitivity import SensitivityTarget, SensitivityTargetMetadata
from app.scenarios.registry import OverrideValidationError, apply_registered_override

INTEGER_FIELDS = {("resourcePool", "capacity"), ("stage", "maximumReworkAttempts")}
FIELD_METADATA: dict[tuple[str, str], tuple[str, str]] = {
    ("resourcePool", "capacity"): ("Resource-pool capacity", "workers"),
    ("source", "arrivalInterval"): ("Fixed arrival interval", "minutes"),
    ("source", "meanInterarrivalTime"): ("Mean interarrival time", "minutes"),
    ("stage", "processing.fixed.value"): ("Fixed processing duration", "minutes"),
    ("stage", "processing.exponential.mean"): ("Mean processing duration", "minutes"),
    ("stage", "processing.uniform.minimum"): ("Uniform minimum", "minutes"),
    ("stage", "processing.uniform.maximum"): ("Uniform maximum", "minutes"),
    ("stage", "processing.triangular.minimum"): ("Triangular minimum", "minutes"),
    ("stage", "processing.triangular.mode"): ("Triangular mode", "minutes"),
    ("stage", "processing.triangular.maximum"): ("Triangular maximum", "minutes"),
    ("stage", "failure.probability"): ("Failure probability", "ratio"),
    ("stage", "maximumReworkAttempts"): ("Maximum rework attempts", "attempts"),
    ("route", "probability"): ("Route probability", "ratio"),
    ("slaRule", "targetDuration"): ("SLA target duration", "minutes"),
}


@dataclass(frozen=True)
class ValidatedTarget:
    metadata: SensitivityTargetMetadata
    normalized_values: list[int | float]


def _normalized(target: SensitivityTarget, value: float) -> int | float:
    if (target.entity_type, target.field) in INTEGER_FIELDS:
        if not value.is_integer():
            raise OverrideValidationError("sensitivity value must be an integer")
        return int(value)
    return value


def validate_target_and_values(
    model: OperationalModel, target: SensitivityTarget, values: list[float]
) -> ValidatedTarget:
    key = (target.entity_type, target.field)
    if key not in FIELD_METADATA:
        raise OverrideValidationError("unsupported sensitivity target")
    normalized = [_normalized(target, value) for value in values]
    baseline_value: int | float | None = None
    errors: list[OverrideValidationError] = []
    for value in normalized:
        data = deepcopy(model.model_dump(mode="json", by_alias=True))
        try:
            summary = apply_registered_override(
                data,
                ScenarioOverride(
                    entity_type=target.entity_type,
                    entity_id=target.entity_id,
                    field=target.field,
                    value=value,
                ),
            )
            baseline_value = summary["previousValue"]  # type: ignore[assignment]
            break
        except OverrideValidationError as error:
            errors.append(error)
    if errors:
        raise errors[0]
    if baseline_value is None:
        raise OverrideValidationError("invalid sensitivity target")
    label, unit = FIELD_METADATA[key]
    return ValidatedTarget(
        metadata=SensitivityTargetMetadata(
            entity_type=target.entity_type,
            entity_id=target.entity_id,
            field=target.field,
            label=label,
            unit=unit,
            value_type="integer" if key in INTEGER_FIELDS else "number",
            baseline_value=float(baseline_value),
        ),
        normalized_values=normalized,
    )
