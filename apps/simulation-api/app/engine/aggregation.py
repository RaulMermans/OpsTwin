import math
from collections.abc import Callable
from dataclasses import dataclass
from statistics import median
from typing import Literal

from app.domain.repeated import (
    AggregateMetric,
    ConfidenceInterval,
    ConfidenceLevel,
    RiskResult,
    RiskThresholds,
)

Z_VALUES: dict[float, float] = {
    0.90: 1.644854,
    0.95: 1.959964,
    0.99: 2.575829,
}


@dataclass
class RunningMoments:
    count: int = 0
    mean: float = 0.0
    _m2: float = 0.0
    minimum: float = math.inf
    maximum: float = -math.inf

    def add(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        self._m2 += delta * (value - self.mean)
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    @property
    def sample_variance(self) -> float:
        return self._m2 / (self.count - 1) if self.count > 1 else 0.0

    @property
    def standard_deviation(self) -> float:
        return math.sqrt(self.sample_variance)


@dataclass(frozen=True)
class RepresentativeCandidate:
    run_index: int
    seed: int
    vector: dict[str, float]


@dataclass(frozen=True)
class RepresentativeSelection:
    candidate: RepresentativeCandidate
    median_vector: dict[str, float]
    distance: float


def nearest_rank(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("nearest-rank quantile requires at least one value")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1))
    return ordered[index]


def aggregate_metric(
    values: list[float], confidence_level: ConfidenceLevel
) -> AggregateMetric:
    if not values:
        raise ValueError("metric aggregation requires at least one value")
    moments = RunningMoments()
    for value in values:
        moments.add(value)
    standard_error = moments.standard_deviation / math.sqrt(moments.count)
    margin = Z_VALUES[confidence_level] * standard_error
    return AggregateMetric(
        count=moments.count,
        mean=moments.mean,
        sample_variance=moments.sample_variance,
        standard_deviation=moments.standard_deviation,
        minimum=moments.minimum,
        maximum=moments.maximum,
        p10=nearest_rank(values, 0.10),
        p50=nearest_rank(values, 0.50),
        p90=nearest_rank(values, 0.90),
        confidence_interval=ConfidenceInterval(
            level=confidence_level,
            lower=moments.mean - margin,
            upper=moments.mean + margin,
            successful_run_count=moments.count,
            reliable_sample_size=moments.count >= 30,
        ),
    )


def evaluate_risks(
    values: dict[str, list[float]], thresholds: RiskThresholds
) -> list[RiskResult]:
    configurations: list[
        tuple[
            str,
            Literal["below", "above"],
            float | None,
            Callable[[float, float], bool],
        ]
    ] = [
        (
            "slaAttainment",
            "below",
            thresholds.minimum_sla_attainment,
            lambda value, threshold: value < threshold,
        ),
        (
            "averageCycleTime",
            "above",
            thresholds.maximum_average_cycle_time,
            lambda value, threshold: value > threshold,
        ),
        (
            "p95CycleTime",
            "above",
            thresholds.maximum_p95_cycle_time,
            lambda value, threshold: value > threshold,
        ),
        (
            "timeWeightedQueueLength",
            "above",
            thresholds.maximum_time_weighted_queue_length,
            lambda value, threshold: value > threshold,
        ),
        (
            "terminalFailureRate",
            "above",
            thresholds.maximum_terminal_failure_rate,
            lambda value, threshold: value > threshold,
        ),
    ]
    results: list[RiskResult] = []
    for metric, operator, threshold, violates in configurations:
        if threshold is None:
            continue
        metric_values = values[metric]
        violating_runs = sum(violates(value, threshold) for value in metric_values)
        results.append(
            RiskResult(
                metric=metric,
                operator=operator,
                threshold=threshold,
                violating_runs=violating_runs,
                valid_runs=len(metric_values),
                probability=violating_runs / len(metric_values),
            )
        )
    return results


def select_representative(
    candidates: list[RepresentativeCandidate],
) -> RepresentativeSelection:
    if not candidates:
        raise ValueError("representative selection requires a successful run")
    metric_names = list(candidates[0].vector)
    if any(list(candidate.vector) != metric_names for candidate in candidates):
        raise ValueError("representative vectors must have identical metrics")
    medians = {
        metric: float(median(candidate.vector[metric] for candidate in candidates))
        for metric in metric_names
    }
    minima = {
        metric: min(candidate.vector[metric] for candidate in candidates)
        for metric in metric_names
    }
    maxima = {
        metric: max(candidate.vector[metric] for candidate in candidates)
        for metric in metric_names
    }

    def distance(candidate: RepresentativeCandidate) -> float:
        components = []
        for metric in metric_names:
            span = maxima[metric] - minima[metric]
            components.append(
                0.0
                if span == 0
                else (candidate.vector[metric] - medians[metric]) / span
            )
        return math.sqrt(sum(component * component for component in components))

    selected = min(candidates, key=lambda candidate: (distance(candidate), candidate.run_index))
    return RepresentativeSelection(selected, medians, distance(selected))
