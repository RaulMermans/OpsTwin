from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.calibration.contracts import (
    CalibrationValidationReport,
    ObservationWindow,
    ValidationOutcome,
    ValidationTargetResult,
    ValidationThresholds,
)
from app.calibration.estimate import cases_created_in
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


def _percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, max(0, math.ceil((p / 100) * len(sorted_values)) - 1))
    return sorted_values[index]


def observed_holdout_metrics(snapshot: dict[str, Any], start: datetime, end: datetime) -> dict[str, float | None]:  # noqa: E501
    created = cases_created_in(snapshot, start, end)
    resolved: list[float] = []
    completed = 0
    for case in created:
        resolved_at = parse_utc(case.get("resolvedAt"))
        created_at = parse_utc(case.get("createdAt"))
        if (
            case.get("observationStatus") == "resolved"
            and resolved_at is not None
            and created_at is not None
            and start <= resolved_at < end
        ):
            completed += 1
            resolved.append(minutes_between(created_at, resolved_at))
    resolved.sort()
    return {
        "arrival_volume": float(len(created)),
        "throughput": float(completed),
        "cycle_time_median": _percentile(resolved, 50),
        "cycle_time_p90": _percentile(resolved, 90),
        "cycle_sample": float(len(resolved)),
    }


def simulated_metrics(result: SimulationResult) -> dict[str, float | None]:
    completed = [
        item.cycle_time
        for item in result.items
        if item.completed and item.cycle_time is not None
    ]
    completed.sort()
    windowed = [
        item.cycle_time
        for item in result.items
        if item.completed
        and result.observation.measurement_start <= item.created_at < result.observation.measurement_end  # noqa: E501
        and item.completed_at is not None
        and item.completed_at <= result.observation.measurement_end
    ]
    windowed.sort()
    values = windowed or completed
    return {
        "arrival_volume": float(result.observation.created_during_window),
        "throughput": float(result.observation.completed_during_window),
        "cycle_time_median": _percentile(values, 50),
        "cycle_time_p90": _percentile(values, 90),
        "cycle_sample": float(len(values)),
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
) -> ValidationTargetResult:
    abs_err = None if observed is None or simulated is None else abs(simulated - observed)
    rel = _relative(observed, simulated)
    if observed is None or simulated is None:
        outcome: ValidationOutcome = "incompatible_metrics"
        notes = "Observed and simulated quantities are not both available."
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
) -> tuple[CalibrationValidationReport, SimulationResult, int]:
    hold_minutes = minutes_between(hold_start, hold_end)
    mean_ia = model.sources[0].arrival.mean_interarrival_time  # type: ignore[union-attr]
    expected = hold_minutes / float(mean_ia)
    item_count = min(max_items, max(8, int(math.ceil(expected * 1.6)) + 8))
    model.sources[0].item_count = item_count
    result = run_simulation(
        model,
        seed_override=seed,
        observation=ObservationConfig(warmup_duration=0, measurement_duration=hold_minutes),
        result_detail=ResultDetailConfig(mode="summary"),
    )
    observed = observed_holdout_metrics(snapshot, hold_start, hold_end)
    simulated = simulated_metrics(result)
    targets = [
        _target(
            "arrival_volume",
            observed["arrival_volume"],
            simulated["arrival_volume"],
            thresholds.arrival_volume_relative,
            int(observed["arrival_volume"] or 0),
            int(simulated["arrival_volume"] or 0),
            "Zero observed arrivals make percentage error undefined.",
        ),
        _target(
            "throughput",
            observed["throughput"],
            simulated["throughput"],
            thresholds.throughput_relative,
            int(observed["throughput"] or 0),
            int(simulated["throughput"] or 0),
            "Zero observed completions make percentage error undefined.",
        ),
        _target(
            "cycle_time_median",
            observed["cycle_time_median"],
            simulated["cycle_time_median"],
            thresholds.cycle_time_median_relative,
            int(observed["cycle_sample"] or 0),
            int(simulated["cycle_sample"] or 0),
            "Insufficient complete cycle times.",
        ),
        _target(
            "cycle_time_p90",
            observed["cycle_time_p90"],
            simulated["cycle_time_p90"],
            thresholds.cycle_time_p90_relative,
            int(observed["cycle_sample"] or 0),
            int(simulated["cycle_sample"] or 0),
            "Insufficient complete cycle times.",
        ),
    ]
    failed = [item.target_id for item in targets if item.outcome == "failed"]
    inconclusive = [item.target_id for item in targets if item.outcome == "inconclusive"]
    if failed:
        overall: ValidationOutcome = "failed"
        adequacy = "failed"
    elif all(item.outcome == "passed_for_defined_scope" for item in targets):
        overall = "passed_for_defined_scope"
        adequacy = "adequate_for_defined_scope"
    else:
        overall = "inconclusive"
        adequacy = "inconclusive"
    limitations = [
        "Validation is generative against a homogeneous Poisson / exponential template.",
        "Successful holdout does not establish causal validity of future interventions.",
        "The simulation starts empty; historical backlog is not injected.",
        "SLA calendars are not compared.",
    ]
    if train_end > hold_start:
        limitations.append("Overlapping windows were rejected before evaluation.")
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
        excluded_targets=["utilization", "sla_attainment"],
        limitations=limitations + ([f"inconclusive:{','.join(inconclusive)}"] if inconclusive else []),  # noqa: E501
        adequacy=adequacy,
    )
    return report, result, item_count
