from __future__ import annotations

from typing import Any

from app.calibration.contracts import OperationalMapping, StatusMapping, StatusRole

PROCESSING_STAGES = ("triage", "resolution")
REQUIRED_ROLES: tuple[StatusRole, ...] = ("queue", "processing", "completed")


class MappingError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def relevant_status_ids(snapshot: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for status in snapshot.get("statuses") or []:
        if status.get("statusId"):
            ids.add(str(status["statusId"]))
    for case in snapshot.get("cases") or []:
        ref = case.get("currentStatusReference")
        if ref:
            ids.add(str(ref))
    for event in snapshot.get("events") or []:
        if event.get("eventType") != "status_changed":
            continue
        for key in ("previousValue", "newValue"):
            if event.get(key):
                ids.add(str(event[key]))
    return ids


def mapping_index(mapping: OperationalMapping) -> dict[str, StatusMapping]:
    return {item.status_id: item for item in mapping.statuses}


def validate_mapping(snapshot: dict[str, Any], mapping: OperationalMapping) -> dict[str, Any]:
    seen: dict[str, StatusMapping] = {}
    for item in mapping.statuses:
        if item.status_id in seen:
            raise MappingError(
                "unsupported_topology",
                "Duplicate or contradictory status mappings are not allowed.",
                {"statusId": item.status_id},
            )
        seen[item.status_id] = item
        if item.role == "processing":
            if item.stage_id not in PROCESSING_STAGES:
                raise MappingError(
                    "unsupported_topology",
                    "Processing statuses require an explicit triage or resolution stage identifier.",  # noqa: E501
                    {"statusId": item.status_id, "stageId": item.stage_id},
                )
            if not item.reviewed:
                raise MappingError(
                    "mapping_required",
                    "Material processing-stage mappings require explicit review.",
                    {"statusId": item.status_id},
                )
        elif item.stage_id is not None:
            raise MappingError(
                "unsupported_topology",
                "Non-processing statuses cannot carry a processing-stage identifier.",
                {"statusId": item.status_id},
            )
    relevant = relevant_status_ids(snapshot)
    unmapped = sorted(status_id for status_id in relevant if status_id not in seen)
    unknown = sorted(
        status_id
        for status_id, item in seen.items()
        if status_id in relevant and item.role == "unknown"
    )
    roles = {item.role for item in seen.values() if item.status_id in relevant or not relevant}
    missing_roles = [role for role in REQUIRED_ROLES if role not in roles]
    processing = [item for item in mapping.statuses if item.role == "processing"]
    if unmapped or unknown:
        raise MappingError(
            "mapping_required",
            "Relevant statuses are unmapped or unknown.",
            {"unmapped": unmapped, "unknown": unknown},
        )
    if missing_roles:
        raise MappingError(
            "unsupported_topology",
            "The supported template requires queue, processing, and completed roles.",
            {"missingRoles": missing_roles},
        )
    if any(item.role == "review" and item.status_id in relevant for item in mapping.statuses):
        raise MappingError(
            "unsupported_topology",
            "Review paths are not representable by support-triage-resolution.",
            {"review": [item.status_id for item in mapping.statuses if item.role == "review"]},
        )
    stage_ids = [item.stage_id for item in processing]
    if len(processing) > 2:
        raise MappingError(
            "unsupported_topology",
            "More than two processing statuses cannot be represented by support-triage-resolution.",
            {"processing": [item.status_id for item in processing]},
        )
    if len(stage_ids) != len(set(stage_ids)):
        raise MappingError(
            "unsupported_topology",
            "Processing-stage assignments are ambiguous.",
            {"stages": stage_ids},
        )
    if not mapping.reviewed or any(not item.reviewed and item.status_id in relevant for item in mapping.statuses):  # noqa: E501
        raise MappingError(
            "mapping_required",
            "Material operational mappings require explicit review.",
            {},
        )
    return {
        "unmapped": unmapped,
        "processing_stage_ids": [item.stage_id for item in processing if item.stage_id],
    }


def role_of(status_id: str | None, mapping: OperationalMapping) -> StatusRole | None:
    if not status_id:
        return None
    item = mapping_index(mapping).get(status_id)
    return item.role if item else None


def stage_of(status_id: str | None, mapping: OperationalMapping) -> str | None:
    if not status_id:
        return None
    item = mapping_index(mapping).get(status_id)
    if item is None or item.role != "processing":
        return None
    return item.stage_id
