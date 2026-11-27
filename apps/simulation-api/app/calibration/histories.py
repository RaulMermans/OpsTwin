from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from app.calibration.snapshot import content_fingerprint, minutes_between, parse_utc

ProfileId = Literal[
    "golden",
    "observable",
    "partial",
    "noisy",
    "nonstationary",
    "misspecified",
    "mixed",
    "shift",
    "hybrid",
]

WINDOW_START = datetime(2026, 1, 1, tzinfo=UTC)
WINDOW_MINUTES = 10_080  # 7 days


def _iso(stamp: datetime) -> str:
    return stamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _prov(case_id: str, evidence: str = "synthetic") -> dict[str, Any]:
    return {
        "sourceSystem": "synthetic-lab",
        "sourceProject": "lab:cg3",
        "sourceEndpoint": "generated",
        "extractionTimestamp": _iso(WINDOW_START + timedelta(minutes=WINDOW_MINUTES)),
        "sourceRecordReference": case_id,
        "transformationVersion": "cg3.histories.1",
        "evidenceClass": evidence,
        "observationWindow": f"{_iso(WINDOW_START)}/{_iso(WINDOW_START + timedelta(minutes=WINDOW_MINUTES))}",  # noqa: E501
        "derivationMethod": None,
        "transportAuthenticity": "offline_fixture",
    }


def _status(status_id: str, name: str) -> dict[str, Any]:
    return {
        "statusId": status_id,
        "displayName": name,
        "sourceCategory": "new" if status_id == "s-open" else "done" if status_id == "s-done" else "indeterminate",  # noqa: E501
        "operationalClass": "unresolved",
        "mappingStatus": "unresolved",
        "classificationProvenance": "synthetic-fixture",
    }


def _interval(
    interval_id: str,
    case_id: str,
    interval_type: str,
    start: datetime,
    end: datetime | None,
    complete: bool,
) -> dict[str, Any]:
    start_at = _iso(start)
    end_at = _iso(end) if end is not None else None
    begin = parse_utc(start_at)
    finish = parse_utc(end_at) if end_at else None
    duration = minutes_between(begin, finish) if begin is not None and finish is not None else None
    return {
        "intervalId": interval_id,
        "caseId": case_id,
        "intervalType": interval_type,
        "startAt": start_at,
        "endAt": end_at,
        "durationMinutes": duration,
        "censoring": "none" if complete else "right",
        "complete": complete,
        "statusReference": None,
    }


def _event(
    event_id: str,
    case_id: str,
    event_type: str,
    occurred: datetime,
    previous: str | None,
    new: str | None,
    evidence: str = "synthetic",
) -> dict[str, Any]:
    return {
        "eventId": event_id,
        "caseId": case_id,
        "eventType": event_type,
        "occurredAt": _iso(occurred),
        "observedAt": _iso(occurred),
        "previousValue": previous,
        "newValue": new,
        "sourceReference": event_id,
        "durationMinutes": None,
        "provenance": _prov(case_id, evidence),
    }


def ground_truth(profile: ProfileId) -> dict[str, Any]:
    hidden_capacity = profile in {"partial", "noisy"}
    return {
        "profile": profile,
        "arrival_mean_interarrival": 30.0 if profile != "nonstationary" else None,
        "triage_mean": 8.0,
        "resolution_mean": 12.0,
        "triage_capacity": 4,
        "resolution_capacity": 6,
        "identifiable_without_assumptions": profile in {"golden", "observable", "hybrid"},
        "hidden": {
            "capacity": hidden_capacity,
            "service_time": profile in {"partial", "noisy", "mixed"},
        },
        "notes": "Ground truth is not an input to calibrate().",
    }


def _quality(n: int) -> list[dict[str, Any]]:
    return [
        {
            "metricId": "completeness",
            "definition": "Share of cases with a valid created timestamp.",
            "numerator": n,
            "denominator": n or None,
            "value": 1 if n else None,
            "status": "pass" if n else "not_applicable",
            "explanation": "Synthetic generator emits valid created timestamps.",
            "consequence": "Arrival estimation can use createdAt.",
            "recommendedNextAction": "Keep invalid timestamps excluded.",
        }
    ]


def generate_history(profile: ProfileId, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    end = WINDOW_START + timedelta(minutes=WINDOW_MINUTES)
    cases: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    intervals: list[dict[str, Any]] = []
    include_worklogs = profile in {"golden", "observable", "hybrid"}
    misspecified = profile == "misspecified"
    mixed = profile == "mixed"
    noisy = profile == "noisy"

    def interarrival(now_minutes: float) -> float:
        if profile == "nonstationary":
            return rng.expovariate(1 / (20 if now_minutes < WINDOW_MINUTES / 2 else 8))
        if profile == "shift":
            return rng.expovariate(1 / (30 if now_minutes < WINDOW_MINUTES * 0.7 else 12))
        return rng.expovariate(1 / 30.0)

    elapsed = 0.0
    index = 0
    while elapsed < WINDOW_MINUTES - 90:
        elapsed += interarrival(elapsed)
        if elapsed >= WINDOW_MINUTES - 90:
            break
        index += 1
        created = WINDOW_START + timedelta(minutes=elapsed)
        case_id = f"case-{index:04d}"
        evidence = "observed" if mixed and index % 2 == 0 else "synthetic"
        triage = max(0.5, rng.expovariate(1 / 8.0))
        resolution = max(0.5, rng.expovariate(1 / 12.0))
        extra = rng.expovariate(1 / 15.0) if misspecified else 0.0
        auto_complete = profile == "hybrid" and rng.random() < 0.25
        if noisy and rng.random() < 0.2:
            events.append(_event(f"e-{index}-gap", case_id, "status_changed", created, "s-open", None, evidence))  # noqa: E501
        in_progress = created + timedelta(minutes=1)
        after_triage = in_progress + timedelta(minutes=triage)
        done_at = (
            after_triage if auto_complete else after_triage + timedelta(minutes=resolution + extra)
        )
        resolved = done_at < end
        cases.append(
            {
                "schemaVersion": "os.1.0.0",
                "caseId": case_id,
                "sourceReference": case_id,
                "sourceSystem": "synthetic-lab",
                "projectReference": "lab:cg3",
                "requestTypeReference": "rt-help",
                "priorityReference": "p-medium",
                "createdAt": _iso(created),
                "resolvedAt": _iso(done_at) if resolved else None,
                "currentStatusReference": "s-done" if resolved else "s-res",
                "observationStatus": "resolved" if resolved else "open",
                "lifecycleCompleteness": "complete" if resolved and not noisy else "incomplete" if noisy else "complete",  # noqa: E501
                "assigneeReference": "agent-a",
                "updatedAt": _iso(done_at if resolved else created),
                "createdAtInvalid": False,
                "syntheticOrigin": evidence == "synthetic",
                "provenance": _prov(case_id, evidence),
            }
        )
        events.append(_event(f"e-{index}-c", case_id, "case_created", created, None, case_id, evidence))  # noqa: E501
        events.append(_event(f"e-{index}-t", case_id, "status_changed", in_progress, "s-open", "s-triage", evidence))  # noqa: E501
        if auto_complete:
            if resolved:
                events.append(_event(f"e-{index}-d", case_id, "status_changed", after_triage, "s-triage", "s-done", evidence))  # noqa: E501
                events.append(_event(f"e-{index}-x", case_id, "resolved", done_at, None, "done", evidence))  # noqa: E501
        else:
            events.append(_event(f"e-{index}-r", case_id, "status_changed", after_triage, "s-triage", "s-res", evidence))  # noqa: E501
            if misspecified:
                review_at = after_triage + timedelta(minutes=resolution)
                events.append(_event(f"e-{index}-v", case_id, "status_changed", review_at, "s-res", "s-review", evidence))  # noqa: E501
                if resolved:
                    events.append(_event(f"e-{index}-d", case_id, "status_changed", done_at, "s-review", "s-done", evidence))  # noqa: E501
                    events.append(_event(f"e-{index}-x", case_id, "resolved", done_at, None, "done", evidence))  # noqa: E501
            elif resolved:
                events.append(_event(f"e-{index}-d", case_id, "status_changed", done_at, "s-res", "s-done", evidence))  # noqa: E501
                events.append(_event(f"e-{index}-x", case_id, "resolved", done_at, None, "done", evidence))  # noqa: E501
        intervals.append(_interval(f"i-{index}-life", case_id, "elapsed_lifetime", created, done_at if resolved else None, resolved))  # noqa: E501
        intervals.append(_interval(f"i-{index}-open", case_id, "status_residence", created, in_progress, True))  # noqa: E501
        intervals.append(_interval(f"i-{index}-tri", case_id, "status_residence", in_progress, after_triage, True))  # noqa: E501
        if include_worklogs:
            events.append(_event(f"e-{index}-w1", case_id, "worklog_recorded", in_progress, None, str(triage), evidence))  # noqa: E501
            work_triage = _interval(f"i-{index}-wt", case_id, "recorded_work", in_progress, after_triage, True)  # noqa: E501
            work_triage["statusReference"] = "s-triage"
            intervals.append(work_triage)
            if not auto_complete:
                events.append(
                    _event(f"e-{index}-w2", case_id, "worklog_recorded", after_triage, None, str(resolution), evidence)  # noqa: E501
                )
                work_res = _interval(f"i-{index}-wr", case_id, "recorded_work", after_triage, after_triage + timedelta(minutes=resolution), True)  # noqa: E501
                work_res["statusReference"] = "s-res"
                intervals.append(work_res)
        elif noisy and rng.random() < 0.3:
            intervals.append(_interval(f"i-{index}-w", case_id, "recorded_work", in_progress, None, False))  # noqa: E501

    statuses = [
        _status("s-open", "Waiting"),
        _status("s-triage", "Triage"),
        _status("s-res", "Resolution"),
        _status("s-done", "Done"),
    ]
    if misspecified:
        statuses.append(_status("s-review", "Hidden review"))
    snapshot: dict[str, Any] = {
        "schemaVersion": "os.1.0.0",
        "snapshotId": f"snap-{profile}-{seed}",
        "connectorVersion": "cg3.histories.1",
        "sourceSystem": "synthetic-lab",
        "sourceProject": {"reference": "lab:cg3", "key": "LAB", "name": "Calibration lab", "serviceDeskId": None},  # noqa: E501
        "authorizedInstallationRef": None,
        "observationWindow": {
            "start": _iso(WINDOW_START),
            "end": _iso(end),
            "convention": "closed-start-open-end-utc",
        },
        "importTimestamp": _iso(end),
        "importStartedAt": _iso(end),
        "importCompletedAt": _iso(end),
        "importConfiguration": {
            "windowDays": 30,
            "recordLimit": 400,
            "pageLimit": 8,
            "cohortPolicy": "open-during-window",
            "includeWorklogs": include_worklogs,
            "includeSla": False,
        },
        "cases": cases,
        "events": events,
        "statuses": statuses,
        "requestTypes": [{"requestTypeId": "rt-help", "name": "Get IT help"}],
        "intervals": intervals,
        "descriptiveEvidence": [
            {
                "metricId": "observed_case_count",
                "definition": "Number of generated cases.",
                "value": len(cases),
                "unit": "cases",
                "population": "all generated cases",
                "sampleSize": len(cases),
                "observationWindow": f"{_iso(WINDOW_START)}/{_iso(end)}",
                "excludedRecords": 0,
                "coverage": 1,
                "provenance": _prov("snapshot"),
                "interpretationLimitations": "Synthetic generator output.",
            }
        ],
        "dataQuality": _quality(len(cases)),
        "completenessStatus": "complete" if not noisy else "partial",
        "readiness": "potentially_suitable_for_calibration_assessment",
        "provenance": _prov("snapshot", "unknown" if mixed else "synthetic"),
        "contentFingerprint": "0" * 64,
        "limitations": ["Synthetic laboratory history. Not organizational operations."],
        "extraction": {
            "complete": not noisy,
            "truncatedReason": "incomplete_changelog" if noisy else None,
            "pageCount": 1,
            "retryCount": 0,
            "inconsistentSource": False,
            "worklogCapability": "retrieved" if include_worklogs else "not_requested",
            "slaCapability": "not_requested",
            "changelogCapability": "partial" if noisy else "retrieved",
            "searchCompleteness": "complete",
            "changelogCompleteness": "incomplete" if noisy else "complete",
            "requestTypeCompleteness": "complete",
            "worklogCompleteness": "complete" if include_worklogs else "not_requested",
            "slaCompleteness": "not_requested",
        },
    }
    if noisy:
        snapshot["readiness"] = "partial"
    snapshot["contentFingerprint"] = content_fingerprint(snapshot)
    return snapshot


def default_mapping(reviewed: bool = True, include_review: bool = False) -> dict[str, Any]:
    statuses = [
        {"statusId": "s-open", "role": "queue", "stageId": None, "reviewed": reviewed},
        {"statusId": "s-triage", "role": "processing", "stageId": "triage", "reviewed": reviewed},
        {"statusId": "s-res", "role": "processing", "stageId": "resolution", "reviewed": reviewed},
        {"statusId": "s-done", "role": "completed", "stageId": None, "reviewed": reviewed},
    ]
    if include_review:
        statuses.append({"statusId": "s-review", "role": "review", "stageId": None, "reviewed": reviewed})  # noqa: E501
    return {"mappingVersion": "status-role.1", "statuses": statuses, "requestTypeClasses": {"rt-help": "demand"}, "reviewed": reviewed}  # noqa: E501


def approved_capacity_and_service() -> list[dict[str, Any]]:
    return [
        {
            "assumptionId": "triage.processing_time.mean",
            "affectedParameter": "triage.processing_time.mean",
            "proposedValue": 8,
            "unit": "minutes",
            "rationale": "No identifiable active processing evidence.",
            "lowerBound": 4,
            "upperBound": 15,
            "source": "analyst",
            "approvalStatus": "approved",
            "revision": 1,
            "limitations": ["Assumption, not a fitted distribution."],
            "evidenceAvailable": "Status residence only",
            "operationalConsequence": "Understated triage time inflates throughput.",
        },
        {
            "assumptionId": "resolution.processing_time.mean",
            "affectedParameter": "resolution.processing_time.mean",
            "proposedValue": 12,
            "unit": "minutes",
            "rationale": "No identifiable active processing evidence.",
            "lowerBound": 6,
            "upperBound": 20,
            "source": "analyst",
            "approvalStatus": "approved",
            "revision": 1,
            "limitations": ["Assumption, not a fitted distribution."],
            "evidenceAvailable": "Status residence only",
            "operationalConsequence": "Understated resolution time hides queues.",
        },
        {
            "assumptionId": "resource.triage-team.capacity",
            "affectedParameter": "resource.triage-team.capacity",
            "proposedValue": 4,
            "unit": "servers",
            "rationale": "Declared laboratory staffing.",
            "lowerBound": 1,
            "upperBound": 8,
            "source": "synthetic-spec",
            "approvalStatus": "approved",
            "revision": 1,
            "limitations": ["Not estimated from assignees."],
            "evidenceAvailable": "None identifiable",
            "operationalConsequence": "Capacity changes waiting time.",
        },
        {
            "assumptionId": "resource.resolution-team.capacity",
            "affectedParameter": "resource.resolution-team.capacity",
            "proposedValue": 6,
            "unit": "servers",
            "rationale": "Declared laboratory staffing.",
            "lowerBound": 1,
            "upperBound": 10,
            "source": "synthetic-spec",
            "approvalStatus": "approved",
            "revision": 1,
            "limitations": ["Not estimated from assignees."],
            "evidenceAvailable": "None identifiable",
            "operationalConsequence": "Capacity changes waiting time.",
        },
    ]
