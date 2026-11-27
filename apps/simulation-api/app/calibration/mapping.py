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
    index = mapping_index(mapping)
    relevant = relevant_status_ids(snapshot)
    unmapped = sorted(status_id for status_id in relevant if status_id not in index)
    unknown = sorted(
        status_id
        for status_id, item in index.items()
        if status_id in relevant and item.role == "unknown"
    )
    roles = {item.role for item in index.values() if item.status_id in relevant or not relevant}
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
    if len(processing) > 2:
        raise MappingError(
            "unsupported_topology",
            "More than two processing statuses cannot be represented by support-triage-resolution.",
            {"processing": [item.status_id for item in processing]},
        )
    if any(item.role == "processing" and not item.stage_id for item in processing) and len(processing) == 2:  # noqa: E501
        for item, stage_id in zip(processing, PROCESSING_STAGES, strict=True):
            item.stage_id = stage_id
    elif len(processing) == 1:
        processing[0].stage_id = processing[0].stage_id or "triage"
    if not mapping.reviewed:
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
