from __future__ import annotations

from typing import cast

from app.domain.economics import TradeoffClassification

TOLERANCE = 1e-9


def classify_tradeoff(
    cost_delta: float | None,
    objective_delta: float | None,
    objective_direction: str,
) -> TradeoffClassification:
    if (
        cost_delta is None
        or objective_delta is None
        or objective_direction
        not in {
            "higher",
            "lower",
        }
    ):
        return "mixed_or_insufficient_evidence"
    cost = "flat" if abs(cost_delta) <= TOLERANCE else "lower" if cost_delta < 0 else "higher"
    improvement = objective_delta if objective_direction == "higher" else -objective_delta
    objective = (
        "flat" if abs(improvement) <= TOLERANCE else "improved" if improvement > 0 else "degraded"
    )
    labels = {
        ("lower", "improved"): "lower_cost_and_improved",
        ("higher", "improved"): "higher_cost_and_improved",
        ("lower", "degraded"): "lower_cost_and_degraded",
        ("higher", "degraded"): "higher_cost_and_degraded",
        ("flat", "improved"): "cost_flat_and_improved",
        ("flat", "degraded"): "cost_flat_and_degraded",
        ("lower", "flat"): "lower_cost_and_objective_flat",
        ("higher", "flat"): "higher_cost_and_objective_flat",
        ("flat", "flat"): "both_flat",
    }
    return cast(TradeoffClassification, labels[(cost, objective)])


def incremental_cost_per_improvement(
    cost_delta: float | None,
    objective_delta: float | None,
    objective_direction: str,
) -> float | None:
    if cost_delta is None or objective_delta is None:
        return None
    magnitude = objective_delta if objective_direction == "higher" else -objective_delta
    if magnitude <= TOLERANCE:
        return None
    return cost_delta / magnitude


def factual_statement(classification: TradeoffClassification, objective_label: str) -> str:
    statements = {
        "lower_cost_and_improved": f"Lower observed recurring cost and improved {objective_label}.",
        "higher_cost_and_improved": (
            f"Higher observed recurring cost and improved {objective_label}."
        ),
        "lower_cost_and_degraded": f"Lower observed recurring cost and degraded {objective_label}.",
        "higher_cost_and_degraded": (
            f"Higher observed recurring cost and degraded {objective_label}."
        ),
        "cost_flat_and_improved": (
            f"Observed recurring cost was flat and {objective_label} improved."
        ),
        "cost_flat_and_degraded": (
            f"Observed recurring cost was flat and {objective_label} degraded."
        ),
        "lower_cost_and_objective_flat": (
            f"Lower observed recurring cost and flat {objective_label}."
        ),
        "higher_cost_and_objective_flat": (
            f"Higher observed recurring cost and flat {objective_label}."
        ),
        "both_flat": f"Observed recurring cost and {objective_label} were flat.",
        "mixed_or_insufficient_evidence": (
            "Insufficient paired evidence for a stable trade-off classification."
        ),
    }
    return statements[classification]
