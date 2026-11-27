from __future__ import annotations

from typing import Any

from app.calibration.snapshot import sha256_canonical
from app.interventions.catalog import ExperimentExecution, NamedAlternative

MEASUREMENT_MODE = "fixed_workload"


def operational_experiment_identity(
    *,
    fixture_id: str | None,
    model_fingerprint: str,
    alternatives: list[NamedAlternative],
    execution: ExperimentExecution,
    measurement_mode: str = MEASUREMENT_MODE,
) -> str:
    return sha256_canonical(
        {
            "layer": "operational_experiment",
            "fixtureId": fixture_id,
            "modelFingerprint": model_fingerprint,
            "alternatives": [
                {
                    "alternativeId": item.alternative_id,
                    "intervention": item.intervention.model_dump(by_alias=True),
                }
                for item in alternatives
            ],
            "execution": {
                "itemCount": execution.item_count,
                "runCount": execution.run_count,
                "baseSeed": execution.base_seed,
            },
            "measurementMode": measurement_mode,
        }
    )


def economic_assumption_identity(assumptions: dict[str, Any]) -> str:
    return sha256_canonical({"layer": "economic_assumptions", "assumptions": assumptions})


def economic_evaluation_identity(
    experiment_identity: str,
    assumption_identity: str,
    *,
    constraints: dict[str, Any] | None = None,
    explore: dict[str, Any] | None = None,
    selected_strategy: str | None = None,
    calculation_version: str = "cg7.v1",
) -> str:
    return sha256_canonical(
        {
            "layer": "economic_evaluation",
            "operationalExperimentIdentity": experiment_identity,
            "economicAssumptionIdentity": assumption_identity,
            "constraints": constraints or {},
            "explore": explore,
            "selectedStrategy": selected_strategy,
            "calculationVersion": calculation_version,
        }
    )
