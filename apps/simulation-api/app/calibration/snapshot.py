from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

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


def _schema_path() -> Path:
    bundled = Path(__file__).resolve().parent / "data" / "operational-snapshot.schema.json"
    repo = Path(__file__).resolve().parents[4] / "contracts" / "operational-snapshot.schema.json"
    if repo.is_file():
        return repo
    return bundled


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _semantic_error(snapshot: dict[str, Any]) -> str | None:
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
    for key in REQUIRED_PROVENANCE:
        if key not in provenance:
            return f"provenance.{key}: missing required field"
    window = snapshot.get("observationWindow") or {}
    start = parse_utc(window.get("start"))
    end = parse_utc(window.get("end"))
    if start is None or end is None or end <= start:
        return "observationWindow: valid UTC interval required"
    if window.get("convention") != "closed-start-open-end-utc":
        return "observationWindow: closed-start-open-end-utc is required"
    project = (snapshot.get("sourceProject") or {}).get("reference")
    case_ids: set[str] = set()
    for index, item in enumerate(snapshot.get("cases") or []):
        case_id = item.get("caseId")
        if not case_id or case_id in case_ids:
            return f"cases[{index}].caseId: identities must be unique"
        case_ids.add(str(case_id))
        created = parse_utc(item.get("createdAt"))
        if item.get("createdAt") and created is None:
            return f"cases[{index}].createdAt: invalid timestamp"
        resolved = parse_utc(item.get("resolvedAt"))
        if item.get("resolvedAt") and resolved is None:
            return f"cases[{index}].resolvedAt: invalid timestamp"
        if item.get("projectReference") != project:
            return f"cases[{index}].projectReference: must match sourceProject.reference"
        if snapshot.get("completenessStatus") == "complete" and item.get("createdAtInvalid"):
            return "complete snapshots cannot contain invalid created timestamps"
    event_ids: set[str] = set()
    for index, item in enumerate(snapshot.get("events") or []):
        event_id = item.get("eventId")
        if not event_id or event_id in event_ids:
            return f"events[{index}].eventId: identities must be unique"
        event_ids.add(str(event_id))
        if item.get("caseId") not in case_ids:
            return f"events[{index}].caseId: unknown case"
        occurred = parse_utc(item.get("occurredAt"))
        if occurred is None:
            return f"events[{index}].occurredAt: invalid timestamp"
    interval_ids: set[str] = set()
    for index, item in enumerate(snapshot.get("intervals") or []):
        interval_id = item.get("intervalId")
        if not interval_id or interval_id in interval_ids:
            return f"intervals[{index}].intervalId: identities must be unique"
        interval_ids.add(str(interval_id))
        if item.get("caseId") not in case_ids:
            return f"intervals[{index}].caseId: unknown case"
        begin = parse_utc(item.get("startAt"))
        finish = parse_utc(item.get("endAt"))
        if item.get("startAt") and begin is None:
            return f"intervals[{index}].startAt: invalid timestamp"
        if item.get("endAt") and finish is None:
            return f"intervals[{index}].endAt: invalid timestamp"
        duration = item.get("durationMinutes")
        if begin is not None and finish is not None:
            if finish < begin:
                return f"intervals[{index}]: endAt precedes startAt"
            expected = minutes_between(begin, finish)
            if isinstance(duration, int | float) and abs(float(duration) - expected) > 1 / 60:
                return f"intervals[{index}].durationMinutes: inconsistent with timestamps"
        if snapshot.get("completenessStatus") == "complete" and snapshot.get("extraction", {}).get("complete") is False:  # noqa: E501
            return "complete snapshots cannot declare incomplete extraction"
    if snapshot.get("completenessStatus") == "invalid":
        return "invalid snapshots are not usable calibration evidence"
    return None


def validate_snapshot_structure(snapshot: dict[str, Any]) -> str | None:
    if not isinstance(snapshot, dict):
        return "snapshot: expected an object"
    try:
        _validator().validate(snapshot)
    except ValidationError as error:
        path = ".".join(str(part) for part in error.absolute_path) or "snapshot"
        return f"{path}: {error.message}"
    return _semantic_error(snapshot)


def canonicalize(value: Any) -> Any:  # noqa: ANN401
    volatile = {
        "snapshotId",
        "importTimestamp",
        "importStartedAt",
        "importCompletedAt",
        "extractionTimestamp",
        "observedAt",
    }
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value == int(value) and abs(value) < 2**53:
            return int(value)
        return value
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {
            key: canonicalize(item)
            for key, item in sorted(value.items())
            if key not in volatile
        }
    return value


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
