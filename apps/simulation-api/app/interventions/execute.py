from __future__ import annotations

from typing import Any, Literal

from app.calibration.construct import CANONICAL_ITEM_COUNT, model_fingerprint
from app.calibration.contracts import CalibrationArtifact
from app.domain.comparison import ScenarioComparisonRequest
from app.domain.models import ContractModel, OperationalModel
from app.domain.repeated import AggregateMetric
from app.interventions.catalog import (
    APPROXIMATION_EFFECTIVE_MEAN,
    APPROXIMATION_ROUTE_SHIFT,
    PLACEHOLDER_ITEM_COUNT,
    ExperimentExecution,
    InterventionConfig,
    InterventionError,
    baseline_inventory,
    materialize_overrides,
)
from app.scenarios.coordinator import run_scenario_comparison
from app.scenarios.materializer import canonical_model_hash

ALLOWED_READINESS = {
    "model_constructed",
    "validation_pending",
    "validation_failed",
    "validated_for_defined_scope",
}


class InterventionEvidence(ContractModel):
    contract_version: Literal["cg4.v1"] = "cg4.v1"
    synthetic: Literal[True] = True
    fixture_id: str | None = None
    intervention_kind: str
    intervention_name: str
    approximations: list[str]
    baseline_readiness: str
    baseline_class: str
    historically_adequate: bool
    exploratory: bool
    disclosures: list[str]
    baseline_inventory: dict[str, Any]
    applied_overrides: list[dict[str, Any]]
    calibrated_model_fingerprint: str
    executed_model_fingerprint: str
    comparison_baseline_hash: str
    identities_agree: bool
    experiment: ExperimentExecution
    schema_version: Literal["0.5.0"] = "0.5.0"
    valid_paired_run_count: int
    baseline_cycle_time: dict[str, Any]
    scenario_cycle_time: dict[str, Any]
    paired_difference: dict[str, Any]
    probability_of_improvement: float
    improvement_interpretation: str
    sla_attainment_baseline: float | None = None
    sla_attainment_scenario: float | None = None
    integrity_status: str
    work_units: int


def classify_baseline(artifact: CalibrationArtifact) -> tuple[str, bool, bool]:
    if artifact.constructed_model is None or artifact.model_fingerprint is None:
        raise InterventionError(
            "baseline_not_executable",
            "No constructed model is available. Interventions cannot run against a structurally invalid baseline.",  # noqa: E501
        )
    if artifact.readiness_status not in ALLOWED_READINESS:
        raise InterventionError(
            "baseline_not_executable",
            f"Baseline readiness {artifact.readiness_status} is not executable.",
        )
    report = artifact.validation_report
    outcome = report.overall_outcome if report else "not_run"
    if (
        artifact.readiness_status == "validated_for_defined_scope"
        and outcome == "passed_for_defined_scope"
    ):  # noqa: E501
        return "historically_adequate_for_defined_scope", True, False
    if artifact.readiness_status == "validation_failed" or outcome == "failed":
        return "historically_failed_model", False, True
    if outcome == "inconclusive":
        return "inconclusive_model", False, True
    if artifact.assumptions:
        return "assumption_based_exploratory_model", False, True
    return "valid_constructed_model", False, True


def bind_execution_model(model: OperationalModel, item_count: int) -> OperationalModel:
    if item_count == PLACEHOLDER_ITEM_COUNT or item_count == CANONICAL_ITEM_COUNT:
        raise InterventionError(
            "placeholder_demand_refused",
            "Experiment execution cannot use the canonical placeholder itemCount.",
        )
    payload = model.model_dump(by_alias=True)
    payload["sources"][0]["itemCount"] = item_count
    return OperationalModel.model_validate(payload)


def _metric(metric: AggregateMetric) -> dict[str, Any]:
    interval = metric.confidence_interval
    return {
        "mean": metric.mean,
        "lower": interval.lower,
        "upper": interval.upper,
        "reliableSampleSize": interval.reliable_sample_size,
    }


def run_intervention_experiment(
    artifact: CalibrationArtifact,
    intervention: InterventionConfig,
    execution: ExperimentExecution,
    *,
    fixture_id: str | None = None,
) -> InterventionEvidence:
    baseline_class, historically_adequate, exploratory = classify_baseline(artifact)
    model = artifact.constructed_model
    assert model is not None
    assert artifact.model_fingerprint is not None
    if model.sources[0].item_count != PLACEHOLDER_ITEM_COUNT:
        raise InterventionError(
            "model_identity_violation",
            "The calibrated canonical model must keep placeholder itemCount=1. Execution volume is a separate identity.",  # noqa: E501
        )
    executed = bind_execution_model(model, execution.item_count)
    executed_fingerprint = model_fingerprint(executed)
    if executed_fingerprint != artifact.model_fingerprint:
        raise InterventionError(
            "model_identity_violation",
            "The model presented by calibration is not the model bound for execution.",
        )
    overrides, approximations, name = materialize_overrides(executed, intervention)
    request = ScenarioComparisonRequest.model_validate(
        {
            "schemaVersion": "0.5.0",
            "baselineModel": executed.model_dump(by_alias=True),
            "scenarios": [
                {
                    "id": intervention.kind,
                    "name": name,
                    "overrides": overrides,
                }
            ],
            "execution": {
                "baseSeed": execution.base_seed,
                "runCount": execution.run_count,
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
    if canonical_model_hash(request.baseline_model) != canonical_model_hash(executed):
        raise InterventionError(
            "model_identity_violation", "Comparison baseline hash diverged before execution."
        )  # noqa: E501
    result = run_scenario_comparison(request)
    scenario = result.scenarios[0]
    if scenario.status != "valid" or scenario.variant is None:
        raise InterventionError(
            "comparison_failed", "The comparison did not produce valid paired evidence."
        )  # noqa: E501
    cycle = scenario.paired_metrics["averageCycleTime"]
    baseline_cycle = result.baseline.system_metrics["averageCycleTime"]
    scenario_cycle = scenario.variant.system_metrics["averageCycleTime"]
    sla_baseline = result.baseline.system_metrics.get("slaAttainment")
    sla_scenario = scenario.variant.system_metrics.get("slaAttainment")
    disclosures = [
        "Interventions are translated into existing Core overrides. There is no second simulation engine.",  # noqa: E501
        "The system starts empty. Warm-up is not applied.",
        execution.justification,
        "A faster task is not automatically a better operation.",
        "Historical holdout adequacy does not establish causal validity of an intervention.",
    ]
    if APPROXIMATION_EFFECTIVE_MEAN in approximations:
        disclosures.append(
            "AI-assisted processing uses an effective-mean model: "
            "(1-coverage)×human_mean + coverage×(assisted_mean + review_overhead). "
            "It does not reproduce mixture variance or per-case AI execution."
        )
    if APPROXIMATION_ROUTE_SHIFT in approximations:
        disclosures.append(
            "Hybrid automation shifts existing triage success-route probabilities. "
            "It does not add an automation stage or explicit per-case bot execution."
        )
    if exploratory:
        disclosures.append(
            f"Exploratory comparison on a {baseline_class.replace('_', ' ')}. "
            "Do not treat these counterfactuals as historically validated predictions."
        )
    if historically_adequate:
        disclosures.append(
            "The baseline matched holdout metrics for a defined empty-system generative scope. "
            "That does not validate the intervention."
        )
    return InterventionEvidence(
        fixture_id=fixture_id,
        intervention_kind=intervention.kind,
        intervention_name=name,
        approximations=approximations,
        baseline_readiness=artifact.readiness_status,
        baseline_class=baseline_class,
        historically_adequate=historically_adequate,
        exploratory=exploratory,
        disclosures=disclosures,
        baseline_inventory=baseline_inventory(model),
        applied_overrides=overrides,
        calibrated_model_fingerprint=artifact.model_fingerprint,
        executed_model_fingerprint=executed_fingerprint,
        comparison_baseline_hash=result.baseline_model_hash,
        identities_agree=executed_fingerprint == artifact.model_fingerprint,
        experiment=execution,
        valid_paired_run_count=cycle.improvement.valid_paired_run_count,
        baseline_cycle_time=_metric(baseline_cycle),
        scenario_cycle_time=_metric(scenario_cycle),
        paired_difference=_metric(cycle.absolute_delta),
        probability_of_improvement=cycle.improvement.probability_of_improvement,
        improvement_interpretation=(
            "Share of valid paired runs where scenario average cycle time was lower than the human-only baseline. "  # noqa: E501
            "This is not a forecast of a live AI deployment."
        ),
        sla_attainment_baseline=None if sla_baseline is None else sla_baseline.mean,
        sla_attainment_scenario=None if sla_scenario is None else sla_scenario.mean,
        integrity_status=result.integrity.status,
        work_units=result.work_budget.estimated_work_units,
    )
