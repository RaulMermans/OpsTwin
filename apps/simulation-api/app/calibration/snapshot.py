from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

REQUIRED_ROOT = (
    "schemaVersion",
    "snapshotId",
    "connectorVersion",
    "sourceSystem",
    "sourceProject",
    "observationWindow",
    "importTimestamp",
    "importConfiguration",
    "cases",
    "events",
    "statuses",
    "requestTypes",
    "intervals",
    "descriptiveEvidence",
    "dataQuality",
    "completenessStatus",
    "readiness",
    "provenance",
    "contentFingerprint",
)
REQUIRED_CASE = (
    "schemaVersion",
    "caseId",
    "sourceReference",
    "sourceSystem",
    "projectReference",
    "requestTypeReference",
    "priorityReference",
    "createdAt",
    "resolvedAt",
    "currentStatusReference",
    "observationStatus",
    "lifecycleCompleteness",
    "provenance",
)
REQUIRED_EVENT = (
    "eventId",
    "caseId",
    "eventType",
    "occurredAt",
    "observedAt",
    "previousValue",
    "newValue",
    "sourceReference",
    "provenance",
)
REQUIRED_INTERVAL = (
    "intervalId",
    "caseId",
    "intervalType",
    "startAt",
    "endAt",
    "durationMinutes",
    "censoring",
    "complete",
)
REQUIRED_PROVENANCE = ("sourceSystem", "evidenceClass", "transformationVersion")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def minutes_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 60.0


def _missing(record: dict[str, Any], keys: tuple[str, ...], path: str) -> str | None:
    for key in keys:
        if key not in record:
            return f"{path}.{key}: missing required field"
    return None


def validate_snapshot_structure(snapshot: dict[str, Any]) -> str | None:
    if not isinstance(snapshot, dict):
        return "snapshot: expected an object"
    missing = _missing(snapshot, REQUIRED_ROOT, "snapshot")
    if missing:
        return missing
    if snapshot.get("schemaVersion") != "os.1.0.0":
        return "schemaVersion: unsupported snapshot schema"
    if snapshot.get("completenessStatus") not in {"complete", "partial", "empty", "invalid"}:
        return "completenessStatus: invalid value"
    fingerprint = snapshot.get("contentFingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        return "contentFingerprint: expected 64 hex characters"
    provenance = snapshot.get("provenance")
    if not isinstance(provenance, dict):
        return "provenance: expected an object"
    missing = _missing(provenance, REQUIRED_PROVENANCE, "provenance")
    if missing:
        return missing
    window = snapshot.get("observationWindow")
    if not isinstance(window, dict) or window.get("convention") != "closed-start-open-end-utc":
        return "observationWindow: closed-start-open-end-utc is required"
    for index, item in enumerate(snapshot.get("cases") or []):
        if not isinstance(item, dict):
            return f"cases[{index}]: expected an object"
        missing = _missing(item, REQUIRED_CASE, f"cases[{index}]")
        if missing:
            return missing
        if item.get("schemaVersion") != "os.1.0.0":
            return f"cases[{index}].schemaVersion: unsupported"
        missing = _missing(item.get("provenance") or {}, REQUIRED_PROVENANCE, f"cases[{index}].provenance")  # noqa: E501
        if missing:
            return missing
    for index, item in enumerate(snapshot.get("events") or []):
        if not isinstance(item, dict):
            return f"events[{index}]: expected an object"
        missing = _missing(item, REQUIRED_EVENT, f"events[{index}]")
        if missing:
            return missing
    for index, item in enumerate(snapshot.get("intervals") or []):
        if not isinstance(item, dict):
            return f"intervals[{index}]: expected an object"
        missing = _missing(item, REQUIRED_INTERVAL, f"intervals[{index}]")
        if missing:
            return missing
    return None


def canonicalize(value: Any) -> Any:  # noqa: ANN401
    volatile = {
        "snapshotId",
        "importTimestamp",
        "importStartedAt",
        "importCompletedAt",
        "extractionTimestamp",
        "observedAt",
    }
    if value is None or not isinstance(value, dict | list):
        return value
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    return {
        key: canonicalize(item)
        for key, item in sorted(value.items())
        if key not in volatile
    }


def content_fingerprint(snapshot: dict[str, Any]) -> str:
    extraction = snapshot.get("extraction") or {}
    payload = canonicalize(
        {
            "schemaVersion": snapshot.get("schemaVersion"),
            "connectorVersion": snapshot.get("connectorVersion"),
            "sourceSystem": snapshot.get("sourceSystem"),
            "sourceProject": snapshot.get("sourceProject"),
            "observationWindow": snapshot.get("observationWindow"),
            "importConfiguration": snapshot.get("importConfiguration"),
            "evidenceClass": (snapshot.get("provenance") or {}).get("evidenceClass"),
            "extraction": {
                "complete": extraction.get("complete"),
                "truncatedReason": extraction.get("truncatedReason"),
                "changelogCapability": extraction.get("changelogCapability"),
                "worklogCapability": extraction.get("worklogCapability"),
                "slaCapability": extraction.get("slaCapability"),
                "searchCompleteness": extraction.get("searchCompleteness"),
                "changelogCompleteness": extraction.get("changelogCompleteness"),
            },
            "cases": snapshot.get("cases"),
            "events": snapshot.get("events"),
            "statuses": snapshot.get("statuses"),
            "requestTypes": snapshot.get("requestTypes"),
            "intervals": snapshot.get("intervals"),
            "dataQuality": [
                {
                    "metricId": item.get("metricId"),
                    "value": item.get("value"),
                    "status": item.get("status"),
                    "numerator": item.get("numerator"),
                    "denominator": item.get("denominator"),
                }
                for item in snapshot.get("dataQuality") or []
            ],
        }
    )
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def sha256_canonical(value: Any) -> str:  # noqa: ANN401
    encoded = json.dumps(canonicalize(value), separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
