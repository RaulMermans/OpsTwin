from __future__ import annotations

from math import isfinite
from typing import Any, Literal

from app.calibration.construct import CANONICAL_ITEM_COUNT, model_fingerprint
from app.calibration.contracts import CalibrationArtifact
from app.domain.comparison import ScenarioComparisonRequest, VariantAggregateResult
from app.domain.models import ContractModel, OperationalModel
from app.domain.repeated import AggregateMetric
from app.interventions.catalog import (
    APPROXIMATION_EFFECTIVE_MEAN,
    APPROXIMATION_ROUTE_SHIFT,
    PLACEHOLDER_ITEM_COUNT,
    ExperimentExecution,
    InterventionConfig,
    InterventionError,
    NamedAlternative,
    baseline_inventory,
    materialize_overrides,
)
from app.interventions.identity import MEASUREMENT_MODE, operational_experiment_identity
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


SYSTEM_METRIC_UNITS = {
    "averageCycleTime": "minutes",
    "p95CycleTime": "minutes",
    "averageWaitingTime": "minutes",
    "completionRate": "items_per_minute",
    "completedItems": "items",
    "terminallyFailedItems": "items",
    "slaAttainment": "proportion",
    "timeWeightedQueueLength": "items",
    "timeWeightedWip": "items",
    "measurementDuration": "minutes",
}

STAGE_METRIC_UNITS = {
    "averageWaitingTime": "minutes",
    "averageProcessingTime": "minutes",
    "timeWeightedQueueLength": "items",
    "visitCount": "visits",
}

RESOURCE_METRIC_UNITS = {
    "utilization": "proportion",
    "idleProportion": "proportion",
    "meanRequestWait": "minutes",
    "requestCount": "requests",
    "busyTime": "minutes",
}


class PackedMetric(ContractModel):
    mean: float
    p50: float | None = None
    lower: float | None = None
    upper: float | None = None
    unit: str
    reliable_sample_size: bool | None = None


class AlternativeEvidence(ContractModel):
    alternative_id: str
    intervention_kind: str
    intervention_name: str
    intervention: dict[str, Any] = {}
    status: Literal["valid", "failed"]
    message: str | None = None
    approximations: list[str] = []
    applied_overrides: list[dict[str, Any]] = []
    system_metrics: dict[str, PackedMetric | None] = {}
    stage_metrics: dict[str, dict[str, PackedMetric | None]] = {}
    resource_metrics: dict[str, dict[str, PackedMetric | None]] = {}
    paired_cycle_time: PackedMetric | None = None
    probability_of_improvement: float | None = None
    valid_paired_run_count: int | None = None


class MultiExperimentEvidence(ContractModel):
    contract_version: Literal["cg5.v1"] = "cg5.v1"
    synthetic: Literal[True] = True
    fixture_id: str | None = None
    experiment_id: str
    experiment_identity: str
    request_id: str | None = None
    experiment_status: Literal["complete", "partial", "failed"]
    measurement_mode: Literal["fixed_workload"] = "fixed_workload"
    demand_exposure: Literal["finite_poisson_arrivals"] = "finite_poisson_arrivals"
    drain_after_boundary: Literal[True] = True
    comparable_population: str = (
        "Successful and unsuccessful completions of the same finite arrival workload."
    )
    incomparable_without_shared_horizon: list[str] = [
        "completionRate",
        "utilization",
        "timeWeightedQueueLength",
        "resource_provisioning_cost",
    ]
    approximations: list[str]
    baseline_readiness: str
    baseline_class: str
    historically_adequate: bool
    exploratory: bool
    disclosures: list[str]
    baseline_inventory: dict[str, Any]
    calibrated_model_fingerprint: str
    executed_model_fingerprint: str
    comparison_baseline_hash: str | None = None
    identities_agree: bool
    experiment: ExperimentExecution
    schema_version: Literal["0.5.0"] = "0.5.0"
    baseline_metrics: dict[str, PackedMetric | None] = {}
    baseline_stage_metrics: dict[str, dict[str, PackedMetric | None]] = {}
    baseline_resource_metrics: dict[str, dict[str, PackedMetric | None]] = {}
    alternatives: list[AlternativeEvidence]
    integrity_status: str | None = None
    work_units: int | None = None
    improvement_interpretation: str


def _finite(value: float) -> float:
    if not isfinite(value):
        raise InterventionError("invalid_metric", "A required metric was not a finite number.")
    return value


def _packed(metric: AggregateMetric, unit: str) -> PackedMetric:
    interval = metric.confidence_interval
    return PackedMetric(
        mean=_finite(metric.mean),
        p50=_finite(metric.p50),
        lower=_finite(interval.lower),
        upper=_finite(interval.upper),
        unit=unit,
        reliable_sample_size=interval.reliable_sample_size,
    )


def _pack_system(variant: VariantAggregateResult) -> dict[str, PackedMetric | None]:
    packed: dict[str, PackedMetric | None] = {}
    for key, unit in SYSTEM_METRIC_UNITS.items():
        metric = variant.system_metrics.get(key)
        packed[key] = None if metric is None else _packed(metric, unit)
    return packed


def _pack_stages(variant: VariantAggregateResult) -> dict[str, dict[str, PackedMetric | None]]:
    packed: dict[str, dict[str, PackedMetric | None]] = {}
    for stage in variant.stage_metrics:
        packed[stage.stage_id] = {
            key: None if stage.metrics.get(key) is None else _packed(stage.metrics[key], unit)
            for key, unit in STAGE_METRIC_UNITS.items()
        }
    return packed


def _pack_resources(variant: VariantAggregateResult) -> dict[str, dict[str, PackedMetric | None]]:
    packed: dict[str, dict[str, PackedMetric | None]] = {}
    for resource in variant.resource_pool_metrics:
        packed[resource.resource_pool_id] = {
            key: None if resource.metrics.get(key) is None else _packed(resource.metrics[key], unit)
            for key, unit in RESOURCE_METRIC_UNITS.items()
        }
    return packed


def _comparison_request(
    executed: OperationalModel,
    scenarios: list[dict[str, Any]],
    execution: ExperimentExecution,
) -> ScenarioComparisonRequest:
    return ScenarioComparisonRequest.model_validate(
        {
            "schemaVersion": "0.5.0",
            "baselineModel": executed.model_dump(by_alias=True),
            "scenarios": scenarios,
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


def _bind_executed(
    artifact: CalibrationArtifact, execution: ExperimentExecution
) -> OperationalModel:
    model = artifact.constructed_model
    assert model is not None
    if model.sources[0].item_count != PLACEHOLDER_ITEM_COUNT:
        raise InterventionError(
            "model_identity_violation",
            "The calibrated canonical model must keep placeholder itemCount=1. Execution volume is a separate identity.",  # noqa: E501
        )
    return bind_execution_model(model, execution.item_count)


def _disclosures(
    approximations: list[str],
    execution: ExperimentExecution,
    exploratory: bool,
    historically_adequate: bool,
    baseline_class: str,
) -> list[str]:
    disclosures = [
        "Interventions are translated into existing Core overrides. There is no second simulation engine.",  # noqa: E501
        "The system starts empty. Warm-up is not applied.",
        execution.justification,
        "A faster task is not automatically a better operation.",
        "Historical holdout adequacy does not establish causal validity of an intervention.",
        "Simulation improvement frequency is not the probability that a live AI deployment will succeed.",  # noqa: E501
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
            "It does not add an automation stage or explicit per-case bot execution. "
            "A completion route is successful automated handling only when that route already exists in the model."  # noqa: E501
        )
    disclosures.append(
        "Measurement is a shared finite arrival workload that drains until empty. "
        "Completions are comparable; throughput, utilization, and time-dependent provisioning costs use scenario-specific horizons and are not cash denominators."  # noqa: E501
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
    return disclosures


def run_multi_intervention_experiment(
    artifact: CalibrationArtifact,
    alternatives: list[NamedAlternative],
    execution: ExperimentExecution,
    *,
    fixture_id: str | None = None,
    experiment_id: str,
    request_id: str | None = None,
) -> MultiExperimentEvidence:
    if not alternatives:
        raise InterventionError("invalid_experiment", "At least one alternative is required.")
    ids = [item.alternative_id for item in alternatives]
    if len(ids) != len(set(ids)):
        raise InterventionError("invalid_experiment", "Alternative identifiers must be unique.")
    if len(alternatives) > 3:
        raise InterventionError(
            "invalid_experiment", "At most three alternatives can share one interactive experiment."
        )
    baseline_class, historically_adequate, exploratory = classify_baseline(artifact)
    assert artifact.constructed_model is not None
    assert artifact.model_fingerprint is not None
    executed = _bind_executed(artifact, execution)
    executed_fingerprint = model_fingerprint(executed)
    if executed_fingerprint != artifact.model_fingerprint:
        raise InterventionError(
            "model_identity_violation",
            "The model presented by calibration is not the model bound for execution.",
        )
    identity = operational_experiment_identity(
        fixture_id=fixture_id,
        model_fingerprint=artifact.model_fingerprint,
        alternatives=alternatives,
        execution=execution,
        measurement_mode=MEASUREMENT_MODE,
    )
    failed: list[AlternativeEvidence] = []
    scenarios: list[dict[str, Any]] = []
    prepared: dict[str, tuple[NamedAlternative, list[dict[str, Any]], list[str], str]] = {}
    for alternative in alternatives:
        try:
            overrides, approximations, name = materialize_overrides(
                executed, alternative.intervention
            )
        except InterventionError as error:
            failed.append(
                AlternativeEvidence(
                    alternative_id=alternative.alternative_id,
                    intervention_kind=alternative.intervention.kind,
                    intervention_name=alternative.intervention.kind,
                    intervention=alternative.intervention.model_dump(by_alias=True),
                    status="failed",
                    message=error.message,
                )
            )
            continue
        prepared[alternative.alternative_id] = (alternative, overrides, approximations, name)
        scenarios.append({"id": alternative.alternative_id, "name": name, "overrides": overrides})
    all_approximations = sorted({item for row in prepared.values() for item in row[2]})
    if not scenarios:
        return MultiExperimentEvidence(
            fixture_id=fixture_id,
            experiment_id=experiment_id,
            experiment_identity=identity,
            request_id=request_id,
            experiment_status="failed",
            approximations=all_approximations,
            baseline_readiness=artifact.readiness_status,
            baseline_class=baseline_class,
            historically_adequate=historically_adequate,
            exploratory=exploratory,
            disclosures=_disclosures(
                all_approximations, execution, exploratory, historically_adequate, baseline_class
            ),
            baseline_inventory=baseline_inventory(artifact.constructed_model),
            calibrated_model_fingerprint=artifact.model_fingerprint,
            executed_model_fingerprint=executed_fingerprint,
            identities_agree=executed_fingerprint == artifact.model_fingerprint,
            experiment=execution,
            alternatives=failed,
            improvement_interpretation=(
                "Share of valid paired runs where scenario average cycle time was lower than the human-only baseline. "  # noqa: E501
                "This is not a forecast of a live AI deployment."
            ),
        )
    request = _comparison_request(executed, scenarios, execution)
    if canonical_model_hash(request.baseline_model) != canonical_model_hash(executed):
        raise InterventionError(
            "model_identity_violation", "Comparison baseline hash diverged before execution."
        )
    result = run_scenario_comparison(request)
    alternatives_out = list(failed)
    for entry in result.scenarios:
        prepared_row = prepared[entry.scenario_id]
        alternative, overrides, approximations, name = prepared_row
        if entry.status != "valid" or entry.variant is None:
            alternatives_out.append(
                AlternativeEvidence(
                    alternative_id=entry.scenario_id,
                    intervention_kind=alternative.intervention.kind,
                    intervention_name=name,
                    intervention=alternative.intervention.model_dump(by_alias=True),
                    status="failed",
                    message="The comparison did not produce valid paired evidence for this alternative.",  # noqa: E501
                    approximations=approximations,
                    applied_overrides=overrides,
                )
            )
            continue
        cycle = entry.paired_metrics.get("averageCycleTime")
        alternatives_out.append(
            AlternativeEvidence(
                alternative_id=entry.scenario_id,
                intervention_kind=alternative.intervention.kind,
                intervention_name=name,
                intervention=alternative.intervention.model_dump(by_alias=True),
                status="valid",
                approximations=approximations,
                applied_overrides=overrides,
                system_metrics=_pack_system(entry.variant),
                stage_metrics=_pack_stages(entry.variant),
                resource_metrics=_pack_resources(entry.variant),
                paired_cycle_time=(
                    None if cycle is None else _packed(cycle.absolute_delta, "minutes")
                ),
                probability_of_improvement=(
                    None if cycle is None else _finite(cycle.improvement.probability_of_improvement)
                ),
                valid_paired_run_count=(
                    None if cycle is None else cycle.improvement.valid_paired_run_count
                ),
            )
        )
    order = {item.alternative_id: index for index, item in enumerate(alternatives)}
    alternatives_out.sort(key=lambda item: order.get(item.alternative_id, 99))
    valid_count = sum(1 for item in alternatives_out if item.status == "valid")
    if valid_count == 0:
        status: Literal["complete", "partial", "failed"] = "failed"
    elif valid_count < len(alternatives):
        status = "partial"
    else:
        status = "complete"
    return MultiExperimentEvidence(
        fixture_id=fixture_id,
        experiment_id=experiment_id,
        experiment_identity=identity,
        request_id=request_id,
        experiment_status=status,
        approximations=all_approximations,
        baseline_readiness=artifact.readiness_status,
        baseline_class=baseline_class,
        historically_adequate=historically_adequate,
        exploratory=exploratory,
        disclosures=_disclosures(
            all_approximations, execution, exploratory, historically_adequate, baseline_class
        ),
        baseline_inventory=baseline_inventory(artifact.constructed_model),
        calibrated_model_fingerprint=artifact.model_fingerprint,
        executed_model_fingerprint=executed_fingerprint,
        comparison_baseline_hash=result.baseline_model_hash,
        identities_agree=executed_fingerprint == artifact.model_fingerprint,
        experiment=execution,
        baseline_metrics=_pack_system(result.baseline),
        baseline_stage_metrics=_pack_stages(result.baseline),
        baseline_resource_metrics=_pack_resources(result.baseline),
        alternatives=alternatives_out,
        integrity_status=result.integrity.status,
        work_units=result.work_budget.estimated_work_units,
        improvement_interpretation=(
            "Share of valid paired runs where scenario average cycle time was lower than the human-only baseline. "  # noqa: E501
            "This is not a forecast of a live AI deployment."
        ),
    )
