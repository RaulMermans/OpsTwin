from __future__ import annotations

import csv
import io
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from app.calibration.snapshot import content_fingerprint, minutes_between, parse_utc

REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")
SUPPORTED_ACTIVITIES = {
    "created": "case_created",
    "case_created": "case_created",
    "triage_started": "status_changed",
    "triage_completed": "status_changed",
    "resolution_started": "status_changed",
    "resolution_completed": "status_changed",
    "completed": "resolved",
    "resolved": "resolved",
}
ACTIVITY_STATUS = {
    "created": "s-open",
    "case_created": "s-open",
    "triage_started": "s-triage",
    "triage_completed": "s-triage",
    "resolution_started": "s-res",
    "resolution_completed": "s-res",
    "completed": "s-done",
    "resolved": "s-done",
}
MAX_CSV_BYTES = 128 * 1024
MAX_ROWS = 400
CSV_TEMPLATE = """case_id,activity,timestamp,work_duration_minutes,processing_stage,outcome
CASE-1,created,2026-01-05T08:00:00.000Z,,,
CASE-1,triage_started,2026-01-05T08:04:00.000Z,5,triage,
CASE-1,triage_completed,2026-01-05T08:10:00.000Z,,,
CASE-1,resolution_started,2026-01-05T08:12:00.000Z,18,resolution,
CASE-1,resolved,2026-01-05T08:35:00.000Z,,,completed
CASE-2,created,2026-01-05T09:00:00.000Z,,,
CASE-2,triage_started,2026-01-05T09:06:00.000Z,7,triage,
CASE-2,resolved,2026-01-05T09:20:00.000Z,,,completed
"""


class CsvImportError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _sanitize_cell(value: str) -> str:
    text = value.strip()
    if text[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def _iso(stamp: datetime) -> str:
    return stamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _csv_provenance(*, source_ref: str, window_text: str, extraction_ts: str) -> dict[str, Any]:
    return {
        "sourceSystem": "csv-upload",
        "sourceProject": "csv:upload",
        "sourceEndpoint": "file",
        "extractionTimestamp": extraction_ts,
        "sourceRecordReference": source_ref,
        "transformationVersion": "cg7.csv.1",
        "evidenceClass": "derived",
        "observationWindow": window_text,
        "derivationMethod": "csv-event-log",
        "transportAuthenticity": "unknown",
    }


def parse_csv_event_log(raw: str, *, timezone_name: str = "UTC") -> dict[str, Any]:
    if timezone_name != "UTC":
        raise CsvImportError("unsupported_timezone", "CSV import currently accepts UTC timestamps only.")  # noqa: E501
    if not isinstance(raw, str) or raw == "":
        raise CsvImportError("invalid_file", "CSV body is empty.")
    if len(raw.encode("utf-8")) > MAX_CSV_BYTES:
        raise CsvImportError("payload_too_large", "CSV exceeds the 128 KiB import limit.")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames is None:
        raise CsvImportError("invalid_file", "CSV header is missing.")
    headers = [str(name).strip() for name in reader.fieldnames if name]
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise CsvImportError("invalid_file", f"CSV is missing required columns: {', '.join(missing)}.")  # noqa: E501
    rows: list[dict[str, str]] = []
    for index, row in enumerate(reader, start=2):
        if index - 1 > MAX_ROWS:
            raise CsvImportError("payload_too_large", f"CSV exceeds {MAX_ROWS} data rows.")
        cleaned = {key: _sanitize_cell(str(value or "")) for key, value in row.items() if key}
        if not any(cleaned.values()):
            continue
        rows.append(cleaned)
    if not rows:
        raise CsvImportError("invalid_file", "CSV contains no event rows.")
    return _snapshot_from_rows(rows)


def _snapshot_from_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    cases: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    intervals: list[dict[str, Any]] = []
    stamps: list[datetime] = []
    for index, row in enumerate(rows):
        case_id = row.get("case_id") or ""
        activity = (row.get("activity") or "").lower()
        stamp = parse_utc(row.get("timestamp"))
        if not case_id:
            raise CsvImportError("invalid_file", f"Row {index + 2} is missing case_id.")
        if activity not in SUPPORTED_ACTIVITIES:
            raise CsvImportError(
                "unsupported_activity",
                f"Activity '{activity}' is not in the supported event-log template.",
            )
        if stamp is None:
            raise CsvImportError("invalid_file", f"Row {index + 2} has an invalid UTC timestamp.")
        stamps.append(stamp)
        case = cases.setdefault(
            case_id,
            {
                "schemaVersion": "os.1.0.0",
                "caseId": case_id,
                "sourceReference": case_id,
                "sourceSystem": "csv-upload",
                "projectReference": "csv:upload",
                "createdAt": None,
                "resolvedAt": None,
                "currentStatusReference": "s-open",
                "requestTypeReference": row.get("request_type") or "rt-csv",
                "priorityReference": row.get("priority") or None,
                "observationStatus": "open",
                "lifecycleCompleteness": "incomplete",
                "assigneeReference": None,
                "updatedAt": None,
                "createdAtInvalid": False,
                "syntheticOrigin": False,
            },
        )
        event_type = SUPPORTED_ACTIVITIES[activity]
        status = ACTIVITY_STATUS[activity]
        previous = None if event_type == "case_created" else case["currentStatusReference"]
        occurred = _iso(stamp)
        if event_type == "case_created" or case["createdAt"] is None:
            case["createdAt"] = occurred
        if event_type == "resolved":
            case["resolvedAt"] = occurred
            case["observationStatus"] = "resolved"
        case["updatedAt"] = occurred
        events.append(
            {
                "eventId": f"csv-{index}-{case_id}",
                "caseId": case_id,
                "eventType": event_type,
                "occurredAt": occurred,
                "observedAt": occurred,
                "previousValue": previous,
                "newValue": status,
                "sourceReference": f"csv:{index}",
                "durationMinutes": None,
            }
        )
        case["currentStatusReference"] = status
        duration_text = row.get("work_duration_minutes") or ""
        start_at = parse_utc(row.get("work_started_at"))
        end_at = parse_utc(row.get("work_ended_at"))
        duration = None
        if duration_text:
            try:
                duration = float(duration_text)
            except ValueError as error:
                raise CsvImportError("invalid_file", f"Row {index + 2} has an invalid duration.") from error  # noqa: E501
            if not math.isfinite(duration) or duration < 0:
                raise CsvImportError("invalid_file", f"Row {index + 2} has an invalid duration.")
        elif start_at is not None and end_at is not None:
            duration = minutes_between(start_at, end_at)
        if duration is not None:
            begin = start_at or stamp
            finish = end_at or (begin + timedelta(minutes=duration))
            intervals.append(
                {
                    "intervalId": f"work-{index}-{case_id}",
                    "caseId": case_id,
                    "intervalType": "recorded_work",
                    "startAt": _iso(begin),
                    "endAt": _iso(finish),
                    "durationMinutes": minutes_between(begin, finish),
                    "censoring": "none",
                    "complete": True,
                    "statusReference": status,
                }
            )
    if not stamps:
        raise CsvImportError("invalid_file", "CSV contains no valid timestamps.")
    start = min(stamps).astimezone(UTC)
    last = max(stamps).astimezone(UTC)
    end = last + timedelta(seconds=1)
    window = {
        "start": _iso(start),
        "end": _iso(end),
        "convention": "closed-start-open-end-utc",
    }
    window_text = f"{window['start']}/{window['end']}"
    span_days = max(1, math.ceil((end - start).total_seconds() / 86400))
    window_days = 30 if span_days <= 30 else 60 if span_days <= 60 else 90
    extraction_ts = window["end"]
    for case in cases.values():
        case["lifecycleCompleteness"] = "complete" if case["createdAt"] and case["resolvedAt"] else "incomplete"  # noqa: E501
        case["provenance"] = _csv_provenance(
            source_ref=str(case["caseId"]),
            window_text=window_text,
            extraction_ts=extraction_ts,
        )
    for event in events:
        event["provenance"] = _csv_provenance(
            source_ref=str(event["sourceReference"]),
            window_text=window_text,
            extraction_ts=extraction_ts,
        )
    snapshot = {
        "schemaVersion": "os.1.0.0",
        "snapshotId": "snap_csv_upload",
        "connectorVersion": "csv.1.0.0",
        "sourceSystem": "csv-upload",
        "sourceProject": {"reference": "csv:upload", "key": "CSV", "name": "CSV upload", "serviceDeskId": None},  # noqa: E501
        "authorizedInstallationRef": None,
        "observationWindow": window,
        "importTimestamp": extraction_ts,
        "importStartedAt": window["start"],
        "importCompletedAt": extraction_ts,
        "importConfiguration": {
            "windowDays": window_days,
            "recordLimit": MAX_ROWS,
            "pageLimit": 1,
            "cohortPolicy": "open-during-window",
            "includeWorklogs": bool(intervals),
            "includeSla": False,
        },
        "cases": list(cases.values()),
        "events": events,
        "statuses": [
            {"statusId": "s-open", "displayName": "Open", "sourceCategory": "new", "operationalClass": "unresolved", "mappingStatus": "unresolved", "classificationProvenance": "csv-template"},  # noqa: E501
            {"statusId": "s-triage", "displayName": "Triage", "sourceCategory": "indeterminate", "operationalClass": "unresolved", "mappingStatus": "unresolved", "classificationProvenance": "csv-template"},  # noqa: E501
            {"statusId": "s-res", "displayName": "Resolution", "sourceCategory": "indeterminate", "operationalClass": "unresolved", "mappingStatus": "unresolved", "classificationProvenance": "csv-template"},  # noqa: E501
            {"statusId": "s-done", "displayName": "Done", "sourceCategory": "done", "operationalClass": "unresolved", "mappingStatus": "unresolved", "classificationProvenance": "csv-template"},  # noqa: E501
        ],
        "requestTypes": [{"requestTypeId": "rt-csv", "name": "CSV demand"}],
        "intervals": intervals,
        "descriptiveEvidence": [
            {
                "metricId": "observed_case_count",
                "definition": "Distinct case identifiers in the uploaded event log.",
                "value": len(cases),
                "unit": "cases",
                "population": "uploaded cases",
                "sampleSize": len(cases),
                "observationWindow": window_text,
                "excludedRecords": 0,
                "coverage": 1,
                "provenance": _csv_provenance(
                    source_ref="csv:upload",
                    window_text=window_text,
                    extraction_ts=extraction_ts,
                ),
                "interpretationLimitations": "User-uploaded event log. Not independently audited.",
            }
        ],
        "dataQuality": [],
        "completenessStatus": "partial",
        "readiness": "potentially_suitable_for_calibration_assessment",
        "provenance": _csv_provenance(
            source_ref="csv:upload",
            window_text=window_text,
            extraction_ts=extraction_ts,
        ),
        "contentFingerprint": "0" * 64,
        "limitations": [
            "CSV event logs are user-supplied. They are not historically validated organizational records.",  # noqa: E501
            "Completeness is partial because the file is not an authorized system extract.",
            "Optional work durations do not by themselves identify resource capacity.",
        ],
        "extraction": {
            "complete": True,
            "truncatedReason": None,
            "pageCount": 1,
            "retryCount": 0,
            "inconsistentSource": False,
            "worklogCapability": "retrieved" if intervals else "not_requested",
            "slaCapability": "not_requested",
            "changelogCapability": "retrieved",
            "searchCompleteness": "complete",
            "changelogCompleteness": "complete",
            "requestTypeCompleteness": "complete",
            "worklogCompleteness": "complete" if intervals else "not_requested",
            "slaCompleteness": "not_requested",
        },
    }
    snapshot["contentFingerprint"] = content_fingerprint(snapshot)
    return snapshot
