from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from app.domain.comparison import ScenarioComparisonRequest, ScenarioComparisonResult
from app.domain.models import ContractModel, OperationalModel
from app.domain.repeated import AggregateMetric
from app.scenarios.coordinator import ScenarioComparisonError, run_scenario_comparison

BASELINE_PATH = Path(__file__).with_name("fixtures") / "support-operations-baseline.json"
MAX_RUN_COUNT = 8
TRIAGE_MEAN = 2.0
LEVEL_1_CAPACITY = 4
Intervention = Literal["add-capacity", "faster-triage"]


class AtlassianCompareRequest(ContractModel):
    contract_version: Literal["cg1.v1"] = "cg1.v1"
    experiment_id: Literal["support-operations-synthetic"] = "support-operations-synthetic"
    intervention: Intervention
    extra_capacity: Literal[1, 2] | None = None
    triage_reduction_percent: Literal[10, 25, 40] | None = None
    run_count: int = Field(default=5, ge=2, le=MAX_RUN_COUNT)
    base_seed: int = Field(default=20_260_716, ge=0, le=2**63 - 1)

    @model_validator(mode="after")
    def validate_intervention_parameters(self) -> AtlassianCompareRequest:
        if self.intervention == "add-capacity":
            if self.extra_capacity is None or self.triage_reduction_percent is not None:
                raise ValueError("add-capacity requires extraCapacity of 1 or 2")
        elif self.triage_reduction_percent is None or self.extra_capacity is not None:
            raise ValueError("faster-triage requires triageReductionPercent of 10, 25, or 40")
        return self


class MetricSummary(ContractModel):
    mean: float
    lower: float
    upper: float
    reliable_sample_size: bool


class AtlassianCompareEvidence(ContractModel):
    contract_version: Literal["cg1.v1"] = "cg1.v1"
    experiment_id: str
    intervention: str
    synthetic: Literal[True] = True
    schema_version: Literal["0.5.0"] = "0.5.0"
    base_seed: int
    run_count: int
    valid_paired_run_count: int
    baseline_cycle_time: MetricSummary
    scenario_cycle_time: MetricSummary
    paired_difference: MetricSummary
    probability_of_improvement: float
    improvement_interpretation: str
    sla_attainment_baseline: float | None = None
    sla_attainment_scenario: float | None = None
    integrity_status: str
    work_units: int
    model_hash: str


def load_support_baseline() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return payload


def build_comparison_request(request: AtlassianCompareRequest) -> ScenarioComparisonRequest:
    baseline = load_support_baseline()
    if request.intervention == "add-capacity":
        scenario = {
            "id": "add-capacity",
            "name": "Increase Level 1 capacity",
            "overrides": [
                {
                    "entityType": "resourcePool",
                    "entityId": "level-1-agents",
                    "field": "capacity",
                    "operation": "replace",
                    "value": LEVEL_1_CAPACITY + int(request.extra_capacity or 0),
                }
            ],
        }
    else:
        mean = TRIAGE_MEAN * (1 - int(request.triage_reduction_percent or 0) / 100)
        scenario = {
            "id": "faster-triage",
            "name": "Reduce triage processing duration",
            "overrides": [
                {
                    "entityType": "stage",
                    "entityId": "triage",
                    "field": "processing.exponential.mean",
                    "operation": "replace",
                    "value": mean,
                }
            ],
        }
    return ScenarioComparisonRequest.model_validate(
        {
            "schemaVersion": "0.5.0",
            "baselineModel": baseline,
            "scenarios": [scenario],
            "execution": {
                "baseSeed": request.base_seed,
                "runCount": request.run_count,
                "confidenceLevel": 0.95,
                "minimumSuccessfulRunRatio": 1,
                "minimumPairedRunRatio": 1,
                "observation": {"warmupDuration": 0},
            },
            "objective": {"metric": "averageCycleTime", "direction": "minimize"},
            "guardrails": [],
            "representativeEvidence": {
                "baseline": False,
                "topRankedScenario": False,
                "detailMode": "summary",
                "sampledItemLimit": None,
            },
        }
    )


def _metric_summary(metric: AggregateMetric) -> MetricSummary:
    interval = metric.confidence_interval
    return MetricSummary(
        mean=metric.mean,
        lower=interval.lower,
        upper=interval.upper,
        reliable_sample_size=interval.reliable_sample_size,
    )


def to_evidence(
    request: AtlassianCompareRequest,
    result: ScenarioComparisonResult,
) -> AtlassianCompareEvidence:
    scenario = result.scenarios[0]
    if scenario.status != "valid" or scenario.variant is None:
        raise ScenarioComparisonError(
            "comparison_failed", "The synthetic comparison did not produce valid paired evidence."
        )
    cycle = scenario.paired_metrics["averageCycleTime"]
    baseline_cycle = result.baseline.system_metrics["averageCycleTime"]
    scenario_cycle = scenario.variant.system_metrics["averageCycleTime"]
    sla_baseline = result.baseline.system_metrics.get("slaAttainment")
    sla_scenario = scenario.variant.system_metrics.get("slaAttainment")
    return AtlassianCompareEvidence(
        experiment_id=request.experiment_id,
        intervention=request.intervention,
        base_seed=result.base_seed,
        run_count=result.requested_run_count,
        valid_paired_run_count=cycle.improvement.valid_paired_run_count,
        baseline_cycle_time=_metric_summary(baseline_cycle),
        scenario_cycle_time=_metric_summary(scenario_cycle),
        paired_difference=_metric_summary(cycle.absolute_delta),
        probability_of_improvement=cycle.improvement.probability_of_improvement,
        improvement_interpretation=(
            "Share of valid paired runs where scenario average cycle time was lower than baseline. "
            "This is not a forecast of a live AI deployment."
        ),
        sla_attainment_baseline=None if sla_baseline is None else sla_baseline.mean,
        sla_attainment_scenario=None if sla_scenario is None else sla_scenario.mean,
        integrity_status=result.integrity.status,
        work_units=result.work_budget.estimated_work_units,
        model_hash=result.baseline_model_hash,
    )


def run_synthetic_comparison(request: AtlassianCompareRequest) -> AtlassianCompareEvidence:
    comparison_request = build_comparison_request(request)
    OperationalModel.model_validate(comparison_request.baseline_model.model_dump(by_alias=True))
    result = run_scenario_comparison(comparison_request)
    return to_evidence(request, result)
