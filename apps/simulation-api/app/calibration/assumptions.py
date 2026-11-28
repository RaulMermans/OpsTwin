from __future__ import annotations

import math

from app.calibration.contracts import (
    KNOWN_ASSUMPTION_IDS,
    AssumptionRecord,
    CalibrationRequest,
)

CAPACITY_IDS = {"resource.triage-team.capacity", "resource.resolution-team.capacity"}
DURATION_IDS = {
    "arrival.mean_interarrival_time",
    "triage.processing_time.mean",
    "resolution.processing_time.mean",
}
EXPECTED_UNITS = {
    "arrival.mean_interarrival_time": "minutes",
    "triage.processing_time.mean": "minutes",
    "resolution.processing_time.mean": "minutes",
    "resource.triage-team.capacity": "servers",
    "resource.resolution-team.capacity": "servers",
    "worklog.completeness": "boolean",
}


class AssumptionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def finite_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise AssumptionError("contract_validation_failure", f"{label} must be a numeric value, not a string or boolean.")  # noqa: E501
    number = float(value)
    if not math.isfinite(number):
        raise AssumptionError("contract_validation_failure", f"{label} must be finite.")
    return number


def validate_assumptions(request: CalibrationRequest) -> None:
    latest: dict[str, AssumptionRecord] = {}
    for item in request.assumption_set:
        if item.assumption_id != item.affected_parameter:
            raise AssumptionError(
                "contract_validation_failure",
                f"{item.assumption_id} does not match affected parameter {item.affected_parameter}.",  # noqa: E501
            )
        if item.assumption_id not in KNOWN_ASSUMPTION_IDS:
            if item.approval_status == "approved":
                raise AssumptionError(
                    "unsupported_parameter",
                    f"Approved assumption {item.assumption_id} is not a known template parameter.",
                )
            continue
        expected_unit = EXPECTED_UNITS[item.assumption_id]
        if item.unit != expected_unit:
            raise AssumptionError(
                "contract_validation_failure",
                f"{item.assumption_id} unit must be {expected_unit}.",
            )
        previous = latest.get(item.assumption_id)
        if (
            previous is not None
            and previous.approval_status == "approved"
            and item.approval_status == "approved"
            and previous.proposed_value != item.proposed_value
        ):
            raise AssumptionError(
                "contract_validation_failure",
                f"Conflicting approved revisions for {item.assumption_id}.",
            )
        latest[item.assumption_id] = item
        if item.approval_status != "approved":
            continue
        if item.assumption_id == "worklog.completeness":
            continue
        value = finite_number(item.proposed_value, label=item.assumption_id)
        lower = None if item.lower_bound is None else finite_number(item.lower_bound, label=f"{item.assumption_id}.lower")  # noqa: E501
        upper = None if item.upper_bound is None else finite_number(item.upper_bound, label=f"{item.assumption_id}.upper")  # noqa: E501
        if lower is not None and upper is not None and lower > upper:
            raise AssumptionError("contract_validation_failure", f"{item.assumption_id} lower bound exceeds upper bound.")  # noqa: E501
        if lower is not None and value < lower:
            raise AssumptionError("contract_validation_failure", f"{item.assumption_id} proposed value is below the approved range.")  # noqa: E501
        if upper is not None and value > upper:
            raise AssumptionError("contract_validation_failure", f"{item.assumption_id} proposed value is above the approved range.")  # noqa: E501
        if item.assumption_id in DURATION_IDS and value <= 0:
            raise AssumptionError("contract_validation_failure", f"{item.assumption_id} processing duration must be positive.")  # noqa: E501
        if item.assumption_id in CAPACITY_IDS:
            if value != int(value):
                raise AssumptionError(
                    "contract_validation_failure",
                    f"{item.assumption_id} staffing capacity must be a whole number of servers.",
                )
            if int(value) < 1:
                raise AssumptionError("contract_validation_failure", f"{item.assumption_id} capacity must be at least 1.")  # noqa: E501
    approved = [item for item in latest.values() if item.approval_status == "approved"]
    if approved and not request.estimation_configuration.allow_assumption_based_model:
        raise AssumptionError(
            "missing_assumptions",
            "Assumption-based construction requires allowAssumptionBasedModel.",
        )
