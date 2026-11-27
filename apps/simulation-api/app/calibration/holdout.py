from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.calibration.contracts import (
    CalibrationValidationReport,
    ObservationWindow,
    OperationalMapping,
    ValidationOutcome,
    ValidationTargetResult,
    ValidationThresholds,
)
from app.calibration.estimate import cases_created_in
from app.calibration.mapping import role_of
from app.calibration.snapshot import minutes_between, parse_utc
from app.domain.models import (
    ObservationConfig,
    OperationalModel,
    ResultDetailConfig,
    SimulationResult,
)
from app.engine.simulator import run_simulation


def iso(stamp: datetime) -> str:
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def simulation_seed(calibration_seed: int, replication_index: int) -> int:
    digest = hashlib.sha256(f"cg3.sim:{calibration_seed}:{replication_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2**63 - 1)


def _percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, max(0, math.ceil((p / 100) * len(sorted_values)) - 1))
    return sorted_values[index]


def _events_by_case(snapshot: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in snapshot.get("events") or []:
        grouped[str(event.get("caseId"))].append(event)
    for case_id, events in grouped.items():
        grouped[case_id] = sorted(
            events, key=lambda item: parse_utc(item.get("occurredAt")) or datetime.min.replace(tzinfo=UTC)  # noqa: E501
        )
    return grouped


def historical_open_at(
    snapshot: dict[str, Any],
    cutoff: datetime,
    mapping: OperationalMapping,
) -> tuple[int, int]:
    grouped = _events_by_case(snapshot)
    open_count = 0
    unknown = 0
    for case in snapshot.get("cases") or []:
        created = parse_utc(case.get("createdAt"))
        if created is None or created >= cutoff:
            continue
        open_state = True
        saw_lifecycle = False
        for event in grouped.get(str(case.get("caseId")), []):
            occurred = parse_utc(event.get("occurredAt"))
            if occurred is None or occurred >= cutoff:
                continue
            event_type = event.get("eventType")
            if event_type == "case_created":
                saw_lifecycle = True
                open_state = True
            elif event_type == "reopened":
                saw_lifecycle = True
                open_state = True
            elif event_type == "resolved":
                saw_lifecycle = True
                open_state = False
            elif event_type == "status_changed" and role_of(event.get("newValue"), mapping) == "completed":  # noqa: E501
                saw_lifecycle = True
                open_state = False
        if not saw_lifecycle:
            unknown += 1
        elif open_state:
            open_count += 1
    return open_count, unknown


def observed_holdout_metrics(
    snapshot: dict[str, Any],
    start: datetime,
    end: datetime,
    mapping: OperationalMapping,
) -> dict[str, float | None]:
    created = cases_created_in(snapshot, start, end)
    grouped = _events_by_case(snapshot)
    resolved: list[float] = []
    completed = 0
    unknown = 0
    for case in created:
        created_at = parse_utc(case.get("createdAt"))
        terminal: datetime | None = None
        done = False
        saw = False
        for event in grouped.get(str(case.get("caseId")), []):
            occurred = parse_utc(event.get("occurredAt"))
            if occurred is None or not (start <= occurred < end):
                continue
            event_type = event.get("eventType")
            if event_type == "resolved" or (
                event_type == "status_changed" and role_of(event.get("newValue"), mapping) == "completed"  # noqa: E501
            ):
                saw = True
                done = True
                terminal = occurred
            elif event_type == "reopened":
                saw = True
                done = False
        if done and created_at is not None and terminal is not None:
            completed += 1
            resolved.append(minutes_between(created_at, terminal))
        elif not saw:
            unknown += 1
    resolved.sort()
    return {
        "arrival_volume": float(len(created)),
        "throughput": float(completed),
        "cycle_time_median": _percentile(resolved, 50),
        "cycle_time_p90": _percentile(resolved, 90),
        "cycle_sample": float(len(resolved)),
        "unknown_outcomes": float(unknown),
    }


def simulated_metrics(result: SimulationResult) -> dict[str, float | None]:
    start = result.observation.measurement_start
    end = result.observation.measurement_end
    if not result.items:
        return {
            "arrival_volume": None,
            "throughput": None,
            "cycle_time_median": None,
            "cycle_time_p90": None,
            "cycle_sample": None,
        }
    created = [item for item in result.items if start <= item.created_at < end]
    completed = [
        item
        for item in created
        if item.completed and item.completed_at is not None and start <= item.completed_at < end
    ]
    cycles = sorted(item.cycle_time for item in completed if item.cycle_time is not None)
    return {
        "arrival_volume": float(len(created)),
        "throughput": float(len(completed)),
        "cycle_time_median": _percentile(cycles, 50),
        "cycle_time_p90": _percentile(cycles, 90),
        "cycle_sample": float(len(cycles)),
    }


def _mean(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def aggregate_metrics(rows: list[dict[str, float | None]]) -> dict[str, float | None]:
    if not rows:
        return {
            "arrival_volume": None,
            "throughput": None,
            "cycle_time_median": None,
            "cycle_time_p90": None,
            "cycle_sample": None,
        }
    return {
        "arrival_volume": _mean([row["arrival_volume"] for row in rows]),
        "throughput": _mean([row["throughput"] for row in rows]),
        "cycle_time_median": _mean([row["cycle_time_median"] for row in rows]),
        "cycle_time_p90": _mean([row["cycle_time_p90"] for row in rows]),
        "cycle_sample": _mean([row["cycle_sample"] for row in rows]),
    }


def _relative(observed: float | None, simulated: float | None) -> float | None:
    if observed is None or simulated is None:
        return None
    if observed == 0:
        return None if simulated == 0 else abs(simulated)
    return abs(simulated - observed) / abs(observed)


def _target(
    target_id: str,
    observed: float | None,
    simulated: float | None,
    threshold: float,
    observed_n: int,
    simulated_n: int,
    zero_policy: str,
    *,
    min_sample: int = 0,
    incompatible: str | None = None,
) -> ValidationTargetResult:
    abs_err = None if observed is None or simulated is None else abs(simulated - observed)
    rel = _relative(observed, simulated)
    if incompatible:
        outcome: ValidationOutcome = "incompatible_metrics"
        notes = incompatible
    elif observed is None or simulated is None:
        outcome = "incompatible_metrics"
        notes = "Observed and simulated quantities are not both available."
    elif min_sample and (observed_n < min_sample or simulated_n < min_sample):
        outcome = "inconclusive"
        notes = f"Sample size below the pre-registered minimum {min_sample}."
    elif observed == 0 and (target_id.endswith("volume") or "throughput" in target_id):
        outcome = "inconclusive" if simulated == 0 else "failed"
        notes = zero_policy
    elif rel is None:
        outcome = "inconclusive"
        notes = "Relative error is undefined near zero; absolute error is retained."
    elif rel <= threshold:
        outcome = "passed_for_defined_scope"
        notes = f"Relative error {rel:.3f} within recorded threshold {threshold:.3f}."
    else:
        outcome = "failed"
        notes = f"Relative error {rel:.3f} exceeds recorded threshold {threshold:.3f}."
    return ValidationTargetResult(
        target_id=target_id,
        observed=observed,
        simulated=simulated,
        absolute_error=abs_err,
        relative_error=rel,
        sample_size_observed=observed_n,
        sample_size_simulated=simulated_n,
        outcome=outcome,
        notes=notes,
    )


def evaluate_holdout(
    snapshot: dict[str, Any],
    model: OperationalModel,
    train_start: datetime,
    train_end: datetime,
    hold_start: datetime,
    hold_end: datetime,
    seed: int,
    thresholds: ValidationThresholds,
    max_items: int,
    mapping: OperationalMapping,
    replications: int,
    backlog: int,
    unknown_backlog: int,
) -> tuple[CalibrationValidationReport, int, list[int], int]:
    hold_minutes = minutes_between(hold_start, hold_end)
    mean_ia = model.sources[0].arrival.mean_interarrival_time  # type: ignore[union-attr]
    expected = hold_minutes / float(mean_ia)
    uncapped = max(8, int(math.ceil(expected * 1.6)) + 8)
    item_count = min(max_items, uncapped)
    truncated = uncapped > max_items
    requested = max(1, replications)
    seeds = [simulation_seed(seed, index) for index in range(requested)]
    rows: list[dict[str, float | None]] = []
    excluded = 0
    for sim_seed in seeds:
        execution = deepcopy(model)
        execution.sources[0].item_count = item_count
        try:
            result = run_simulation(
                execution,
                seed_override=sim_seed,
                observation=ObservationConfig(warmup_duration=0, measurement_duration=hold_minutes),
                result_detail=ResultDetailConfig(mode="summary"),
            )
        except Exception:  # noqa: BLE001
            excluded += 1
            continue
        rows.append(simulated_metrics(result))
    simulated = aggregate_metrics(rows)
    observed = observed_holdout_metrics(snapshot, hold_start, hold_end, mapping)
    initial_incompatible = backlog > 0 or unknown_backlog > 0
    backlog_note = (
        "Core starts empty; historical initial backlog is not injected, so throughput and cycle time are not comparable."  # noqa: E501
        if initial_incompatible
        else None
    )
    truncated_note = (
        "Item cap truncated the intended arrival process; arrival-process adequacy is not claimed."
        if truncated
        else None
    )
    targets = [
        _target(
            "arrival_volume",
            observed["arrival_volume"],
            simulated["arrival_volume"],
            thresholds.arrival_volume_relative,
            int(observed["arrival_volume"] or 0),
            int(simulated["arrival_volume"] or 0),
            "Zero observed arrivals make percentage error undefined.",
            incompatible=truncated_note,
        ),
        _target(
            "throughput",
            observed["throughput"],
            simulated["throughput"],
            thresholds.throughput_relative,
            int(observed["throughput"] or 0),
            int(simulated["throughput"] or 0),
            "Zero observed completions make percentage error undefined.",
            incompatible=backlog_note,
        ),
        _target(
            "cycle_time_median",
            observed["cycle_time_median"],
            simulated["cycle_time_median"],
            thresholds.cycle_time_median_relative,
            int(observed["cycle_sample"] or 0),
            int(simulated["cycle_sample"] or 0),
            "Insufficient complete cycle times.",
            min_sample=thresholds.min_cycle_sample_median,
            incompatible=backlog_note,
        ),
        _target(
            "cycle_time_p90",
            observed["cycle_time_p90"],
            simulated["cycle_time_p90"],
            thresholds.cycle_time_p90_relative,
            int(observed["cycle_sample"] or 0),
            int(simulated["cycle_sample"] or 0),
            "Insufficient complete cycle times.",
            min_sample=thresholds.min_cycle_sample_p90,
            incompatible=backlog_note,
        ),
    ]
    failed = [item.target_id for item in targets if item.outcome == "failed"]
    inconclusive = [item.target_id for item in targets if item.outcome == "inconclusive"]
    incompatible = [item.target_id for item in targets if item.outcome == "incompatible_metrics"]
    if failed:
        overall: ValidationOutcome = "failed"
        adequacy = "failed"
    elif all(item.outcome == "passed_for_defined_scope" for item in targets):
        overall = "passed_for_defined_scope"
        adequacy = "adequate_for_defined_scope"
    elif incompatible and not failed:
        overall = "incompatible_metrics"
        adequacy = "incompatible_initial_conditions" if initial_incompatible else "incompatible_metrics"  # noqa: E501
    else:
        overall = "inconclusive"
        adequacy = "inconclusive"
    validation_class = (
        "empty_system_arrival_only"
        if initial_incompatible
        else "empty_system_generative"
    )
    limitations = [
        "Validation is generative against a homogeneous Poisson / exponential template.",
        "Successful holdout does not establish causal validity of future interventions.",
        "The supported Core class starts empty; historical WIP is not a model initial condition.",
        "SLA calendars are not compared.",
        "Replication variability is simulation noise under fitted parameters, not parameter posterior uncertainty.",  # noqa: E501
    ]
    report = CalibrationValidationReport(
        mode="generative",
        training_window=ObservationWindow(start=iso(train_start), end=iso(train_end)),
        validation_window=ObservationWindow(start=iso(hold_start), end=iso(hold_end)),
        thresholds_recorded_before_evaluation=thresholds,
        historical_metrics=observed,
        simulated_metrics=simulated,
        targets=targets,
        overall_outcome=overall,
        failed_gates=failed,
        excluded_targets=["utilization", "sla_attainment", "total_throughput_including_backlog"],
        limitations=limitations
        + ([f"inconclusive:{','.join(inconclusive)}"] if inconclusive else [])
        + ([f"incompatible:{','.join(incompatible)}"] if incompatible else []),
        adequacy=adequacy,
        validation_class=validation_class,
        replication_count=len(rows),
        requested_replications=requested,
        excluded_replications=excluded,
        simulation_seeds=seeds,
        arrivals_truncated=truncated,
    )
    return report, item_count, seeds, excluded
