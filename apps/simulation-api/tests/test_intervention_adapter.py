from __future__ import annotations

import pytest

from app.calibration.catalog import load_fixture, request_for_fixture
from app.calibration.construct import model_fingerprint
from app.calibration.workflow import calibrate
from app.interventions.catalog import (
    APPROXIMATION_EFFECTIVE_MEAN,
    AssistedIntervention,
    CapacityIntervention,
    ExperimentExecution,
    HybridIntervention,
    InterventionError,
    NamedAlternative,
    effective_mean,
    hybrid_compatible,
    materialize_overrides,
)
from app.interventions.execute import (
    bind_execution_model,
    run_intervention_experiment,
    run_multi_intervention_experiment,
)


def golden_artifact():  # noqa: ANN201
    snapshot = load_fixture("cg3-golden-analytical", 21)
    return calibrate(snapshot, request_for_fixture("cg3-golden-analytical", snapshot, approve=True))


def test_effective_mean_is_the_disclosed_mixture() -> None:
    assert effective_mean(10, 0.5, 0.4, 0.5) == pytest.approx(8.25)


def test_placeholder_demand_is_refused() -> None:
    artifact = golden_artifact()
    assert artifact.constructed_model is not None
    assert artifact.constructed_model.sources[0].item_count == 1
    with pytest.raises(InterventionError, match="placeholder"):
        bind_execution_model(artifact.constructed_model, 1)


def test_execution_volume_does_not_change_model_identity() -> None:
    artifact = golden_artifact()
    assert artifact.constructed_model is not None
    bound = bind_execution_model(artifact.constructed_model, 40)
    assert bound.sources[0].item_count == 40
    assert artifact.constructed_model.sources[0].item_count == 1
    assert model_fingerprint(bound) == artifact.model_fingerprint


def test_capacity_expansion_reuses_pool_overrides() -> None:
    artifact = golden_artifact()
    assert artifact.constructed_model is not None
    overrides, approximations, name = materialize_overrides(
        artifact.constructed_model,
        CapacityIntervention(extra_triage_capacity=1, extra_resolution_capacity=0),
    )
    assert approximations == []
    assert "capacity" in name.lower()
    assert overrides[0]["entityType"] == "resourcePool"
    assert overrides[0]["value"] == artifact.constructed_model.resource_pools[0].capacity + 1


def test_missing_model_is_not_executable() -> None:
    snapshot = load_fixture("cg3-partially-observable", 21)
    artifact = calibrate(
        snapshot, request_for_fixture("cg3-partially-observable", snapshot, approve=False)
    )
    with pytest.raises(InterventionError, match="constructed model"):
        run_intervention_experiment(
            artifact,
            CapacityIntervention(),
            ExperimentExecution(item_count=20, run_count=2),
        )


def test_capacity_comparison_runs_on_calibrated_golden_model() -> None:
    artifact = golden_artifact()
    evidence = run_intervention_experiment(
        artifact,
        CapacityIntervention(extra_triage_capacity=1, extra_resolution_capacity=1),
        ExperimentExecution(item_count=20, run_count=2, base_seed=20261127),
        fixture_id="cg3-golden-analytical",
    )
    assert evidence.identities_agree is True
    assert evidence.experiment.item_count == 20
    assert evidence.baseline_inventory["canonicalItemCount"] == 1
    assert evidence.valid_paired_run_count == 2
    assert evidence.integrity_status == "passed"
    assert evidence.historically_adequate is False or evidence.exploratory is True
    assert (
        "counterfactual" in " ".join(evidence.disclosures).lower() or evidence.historically_adequate
    )  # noqa: E501


def test_ai_assisted_is_labeled_effective_mean() -> None:
    artifact = golden_artifact()
    evidence = run_intervention_experiment(
        artifact,
        AssistedIntervention(
            stage_id="triage", coverage=0.5, processing_reduction=0.4, review_overhead_minutes=0.25
        ),  # noqa: E501
        ExperimentExecution(item_count=20, run_count=2, base_seed=20261127),
    )
    assert APPROXIMATION_EFFECTIVE_MEAN in evidence.approximations
    assert "effective-mean" in " ".join(evidence.disclosures).lower()
    assert evidence.applied_overrides[0]["field"] == "processing.exponential.mean"
    assert (
        evidence.applied_overrides[0]["value"]
        < artifact.constructed_model.stages[0].processing_time.mean
    )  # type: ignore[union-attr]  # noqa: E501


def test_hybrid_refuses_when_completion_route_is_absent() -> None:
    artifact = golden_artifact()
    assert artifact.constructed_model is not None
    route = next(item for item in artifact.constructed_model.routes if item.id == "triage-success")
    has_completion = any(option.target_type == "completion" for option in route.options)
    if has_completion:
        evidence = run_intervention_experiment(
            artifact,
            HybridIntervention(auto_complete_fraction=0.25),
            ExperimentExecution(item_count=20, run_count=2, base_seed=20261127),
        )
        assert "success_route_probability_shift" in evidence.approximations
        assert evidence.applied_overrides[0]["entityType"] == "route"
        return
    with pytest.raises(InterventionError, match="automated resolution"):
        materialize_overrides(artifact.constructed_model, HybridIntervention())


def hybrid_artifact():  # noqa: ANN201
    snapshot = load_fixture("cg5-hybrid-support", 21)
    return calibrate(snapshot, request_for_fixture("cg5-hybrid-support", snapshot, approve=True))


def test_hybrid_fixture_has_completion_route() -> None:
    artifact = hybrid_artifact()
    assert artifact.constructed_model is not None
    assert hybrid_compatible(artifact.constructed_model) is True
    evidence = run_intervention_experiment(
        artifact,
        HybridIntervention(auto_complete_fraction=0.25),
        ExperimentExecution(item_count=20, run_count=2, base_seed=20261127),
        fixture_id="cg5-hybrid-support",
    )
    assert "success_route_probability_shift" in evidence.approximations
    assert evidence.applied_overrides[0]["entityType"] == "route"


def test_multi_experiment_shares_baseline_and_reports_partial_failure() -> None:
    artifact = hybrid_artifact()
    evidence = run_multi_intervention_experiment(
        artifact,
        [
            NamedAlternative(
                alternative_id="human-expansion",
                intervention=CapacityIntervention(
                    extra_triage_capacity=1, extra_resolution_capacity=1
                ),
            ),
            NamedAlternative(
                alternative_id="ai-assisted",
                intervention=AssistedIntervention(
                    stage_id="triage",
                    coverage=0.5,
                    processing_reduction=0.4,
                    review_overhead_minutes=0.25,
                ),
            ),
            NamedAlternative(
                alternative_id="hybrid",
                intervention=HybridIntervention(auto_complete_fraction=0.25),
            ),
        ],
        ExperimentExecution(item_count=20, run_count=2, base_seed=20261127),
        fixture_id="cg5-hybrid-support",
        experiment_id="demo-support-20261127",
        request_id="req-1",
    )
    assert evidence.experiment_status == "complete"
    assert evidence.comparison_baseline_hash is not None
    assert evidence.identities_agree is True
    assert len(evidence.alternatives) == 3
    assert all(item.status == "valid" for item in evidence.alternatives)
    assert evidence.baseline_metrics["averageCycleTime"] is not None
    assert "triage" in evidence.baseline_stage_metrics
    assert evidence.alternatives[0].system_metrics["averageCycleTime"] is not None
    golden = golden_artifact()
    refused = run_multi_intervention_experiment(
        golden,
        [
            NamedAlternative(
                alternative_id="human-expansion",
                intervention=CapacityIntervention(extra_resolution_capacity=1),
            ),
            NamedAlternative(
                alternative_id="hybrid",
                intervention=HybridIntervention(auto_complete_fraction=0.25),
            ),
        ],
        ExperimentExecution(item_count=20, run_count=2, base_seed=20261127),
        fixture_id="cg3-golden-analytical",
        experiment_id="partial-hybrid",
        request_id="req-2",
    )
    assert refused.experiment_status == "partial"
    hybrid = next(item for item in refused.alternatives if item.alternative_id == "hybrid")
    assert hybrid.status == "failed"
    human = next(item for item in refused.alternatives if item.alternative_id == "human-expansion")
    assert human.status == "valid"
