from __future__ import annotations

from typing import Any

from app.domain.comparison import ScenarioOverride


class OverrideValidationError(ValueError):
    """Raised when an override is not authorized by the registry."""


def _entity(values: list[dict[str, Any]], entity_id: str, label: str) -> dict[str, Any]:
    match = next((value for value in values if value["id"] == entity_id), None)
    if match is None:
        raise OverrideValidationError(f"unknown {label} entity ID")
    return match


def _integer(value: int | float, minimum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OverrideValidationError(f"{label} must be an integer")
    if value < minimum:
        raise OverrideValidationError(f"{label} must be at least {minimum}")
    return value


def _number(value: int | float, minimum: float, label: str, *, strict: bool) -> float:
    number = float(value)
    if number < minimum or (strict and number == minimum):
        comparator = "greater than" if strict else "at least"
        raise OverrideValidationError(f"{label} must be {comparator} {minimum}")
    return number


def _replace(target: dict[str, Any], key: str, value: int | float) -> int | float:
    previous = target[key]
    target[key] = value
    if not isinstance(previous, int | float) or isinstance(previous, bool):
        raise OverrideValidationError("override target is not numeric")
    return previous


def apply_registered_override(
    model: dict[str, Any], override: ScenarioOverride
) -> dict[str, object]:
    previous: int | float
    value: int | float = override.value
    if override.entity_type == "resourcePool":
        if override.field != "capacity":
            raise OverrideValidationError("unsupported override field for resourcePool")
        target = _entity(model["resourcePools"], override.entity_id, "resourcePool")
        value = _integer(value, 1, "capacity")
        previous = _replace(target, "capacity", value)
    elif override.entity_type == "source":
        target = _entity(model["sources"], override.entity_id, "source")
        arrival = target["arrival"]
        if override.field == "arrivalInterval":
            if arrival["type"] != "fixed":
                raise OverrideValidationError("arrivalInterval requires a fixed source")
            value = _number(value, 0, "arrivalInterval", strict=True)
            previous = _replace(arrival, "interval", value)
        elif override.field == "meanInterarrivalTime":
            if arrival["type"] != "poisson":
                raise OverrideValidationError(
                    "meanInterarrivalTime requires a Poisson source"
                )
            value = _number(value, 0, "meanInterarrivalTime", strict=True)
            previous = _replace(arrival, "meanInterarrivalTime", value)
        else:
            raise OverrideValidationError("unsupported override field for source")
    elif override.entity_type == "stage":
        target = _entity(model["stages"], override.entity_id, "stage")
        processing_fields = {
            "processing.fixed.value": ("fixed", "value", False),
            "processing.exponential.mean": ("exponential", "mean", True),
            "processing.uniform.minimum": ("uniform", "minimum", False),
            "processing.uniform.maximum": ("uniform", "maximum", False),
            "processing.triangular.minimum": ("triangular", "minimum", False),
            "processing.triangular.mode": ("triangular", "mode", False),
            "processing.triangular.maximum": ("triangular", "maximum", False),
        }
        if override.field in processing_fields:
            distribution, key, strict = processing_fields[override.field]
            processing = target["processingTime"]
            if processing["type"] != distribution:
                raise OverrideValidationError(
                    "processing override does not match the stage distribution"
                )
            value = _number(value, 0, override.field, strict=strict)
            previous = _replace(processing, key, value)
        elif override.field == "failure.probability":
            failure = target.get("failure")
            if failure is None:
                raise OverrideValidationError("failure override requires stage failure")
            number = float(value)
            if not 0 <= number <= 1:
                raise OverrideValidationError("failure probability must be between zero and one")
            value = number
            previous = _replace(failure, "probability", value)
        elif override.field == "maximumReworkAttempts":
            failure = target.get("failure")
            if failure is None:
                raise OverrideValidationError("rework override requires stage failure")
            value = _integer(value, 0, "maximumReworkAttempts")
            previous = _replace(failure, "maximumReworkAttempts", value)
        else:
            raise OverrideValidationError("unsupported override field for stage")
    elif override.entity_type == "route":
        if override.field != "probability":
            raise OverrideValidationError("unsupported override field for route")
        route_id, separator, target_id = override.entity_id.partition(":")
        if not separator or not target_id:
            raise OverrideValidationError("route probability entityId must be routeId:targetId")
        route = _entity(model["routes"], route_id, "route")
        option = next(
            (
                candidate
                for candidate in route["options"]
                if (candidate.get("targetId") or "completion") == target_id
            ),
            None,
        )
        if option is None:
            raise OverrideValidationError("unknown route option entity ID")
        number = float(value)
        if not 0 <= number <= 1:
            raise OverrideValidationError("route probability must be between zero and one")
        value = number
        previous = _replace(option, "probability", value)
    elif override.entity_type == "slaRule":
        if override.field != "targetDuration":
            raise OverrideValidationError("unsupported override field for slaRule")
        target = _entity(model["slaRules"], override.entity_id, "slaRule")
        value = _number(value, 0, "targetDuration", strict=True)
        previous = _replace(target, "targetDuration", value)
    else:  # Pydantic prevents this; retain a registry boundary for direct callers.
        raise OverrideValidationError("unknown entity type")
    return {
        "entityType": override.entity_type,
        "entityId": override.entity_id,
        "field": override.field,
        "previousValue": previous,
        "value": value,
    }
