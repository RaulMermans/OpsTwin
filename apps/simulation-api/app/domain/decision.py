from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, field_validator

from app.domain.models import ContractModel

RealizationMechanism = Literal[
    "none",
    "avoided_hiring",
    "reduced_overtime",
    "reduced_outsourcing",
    "realizable_payroll_reduction",
]
DecisionState = Literal[
    "economically_attractive_under_current_assumptions",
    "operationally_beneficial_financially_unattractive",
    "capacity_releasing_without_cash_savings",
    "attractive_only_under_break_even_conditions",
    "dominated_by_another_modeled_strategy",
    "high_sensitivity_to_uncertain_assumptions",
    "insufficient_evidence_for_a_decision",
    "suitable_for_controlled_pilot_evaluation",
    "not_justified_under_the_selected_assumptions",
]
BreakEvenParameter = Literal[
    "aiSubscriptionMonthly",
    "implementationCost",
    "realizationRate",
    "monthlyStaffCostPerFte",
    "aiCostPerAutomatedCase",
]


class DecisionAssumptions(ContractModel):
    schema_version: Literal["cg6.v1"] = "cg6.v1"
    currency: str = "EUR"
    origin: Literal["synthetic_demonstration"] = "synthetic_demonstration"
    evaluation_months: int = Field(default=12, ge=1, le=36)
    monthly_staff_cost_per_fte: float = Field(default=6_500, ge=0)
    paid_hours_per_month: float = Field(default=160, gt=0, le=744)
    baseline_triage_fte: float = Field(default=1, ge=0)
    baseline_resolution_fte: float = Field(default=1, ge=0)
    ai_subscription_monthly: float = Field(default=800, ge=0)
    ai_cost_per_automated_case: float = Field(default=0, ge=0)
    implementation_cost: float = Field(default=12_000, ge=0)
    realization_mechanism: RealizationMechanism = "none"
    realization_rate: float = Field(default=0, ge=0, le=1)
    value_released_capacity: bool = False

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if re.fullmatch(r"[A-Z]{3}", value) is None:
            raise ValueError("currency must be three uppercase letters")
        return value


class DecisionConstraints(ContractModel):
    maximum_implementation_cost: float | None = Field(default=None, ge=0)
    maximum_recurring_monthly: float | None = Field(default=None, ge=0)
    maximum_cycle_time: float | None = Field(default=None, gt=0)
    minimum_completions: float | None = Field(default=None, ge=0)
    maximum_payback_months: float | None = Field(default=None, ge=0)


class BreakEvenExploreRequest(ContractModel):
    parameter: BreakEvenParameter
    low: float = Field(ge=0)
    high: float = Field(ge=0)
    point_count: int = Field(default=7, ge=3, le=9)


class StrategyEconomics(ContractModel):
    strategy_id: str
    intervention_kind: str
    status: Literal["valid", "unavailable"]
    measurement_mode: Literal["fixed_workload"]
    comparable_completions: bool
    duration_dependent_metrics_comparable: Literal[False] = False
    average_cycle_time: float | None
    successful_completions: float | None
    unsuccessful_outcomes: float | None
    existing_operating_expenditure: float | None
    incremental_staffing_cost: float | None
    incremental_ai_cost: float | None
    one_time_implementation_expenditure: float | None
    recurring_operating_expenditure: float | None
    total_modeled_cost: float | None
    cost_per_successful_completion: float | None
    released_human_hours: float | None
    realizable_cash_benefit: float | None
    potential_capacity_value: float | None
    incremental_investment: float | None
    net_benefit: float | None
    roi: float | None
    payback_months: float | None
    payback_status: Literal["recovered_within_horizon", "no_payback", "not_applicable"]
    decision_state: DecisionState
    notes: list[str]


class BreakEvenPoint(ContractModel):
    parameter_value: float
    net_benefit: float | None
    roi: float | None


class BreakEvenEvidence(ContractModel):
    parameter: BreakEvenParameter
    mode: Literal["financial_only"]
    current_value: float
    points: list[BreakEvenPoint]
    threshold: float | None
    threshold_status: Literal[
        "one_threshold",
        "no_break_even_in_range",
        "insufficient_evidence",
    ]
    explanation: str
    reused_operational_evidence: Literal[True] = True


class DecisionBrief(ContractModel):
    baseline: str
    strategies: list[str]
    operational_findings: list[str]
    economic_findings: list[str]
    key_assumptions: list[str]
    break_even: str | None
    material_risks: list[str]
    suggested_next_action: str
    synthetic: Literal[True] = True


class DecisionEvaluationResult(ContractModel):
    contract_version: Literal["cg6.v1"] = "cg6.v1"
    synthetic: Literal[True] = True
    fixture_id: str | None
    operational_experiment_identity: str
    economic_assumption_identity: str
    economic_evaluation_identity: str
    measurement_mode: Literal["fixed_workload"]
    economic_uncertainty: Literal["conditional_on_summarized_operational_outcomes"]
    integrity_status: Literal["passed"]
    experiment_status: Literal["complete", "partial"]
    historically_adequate: bool
    exploratory: bool
    reused_existing_cost_semantics: Literal[True] = True
    strategies: list[StrategyEconomics]
    break_even: BreakEvenEvidence | None = None
    brief: DecisionBrief
    work_units: int = 0
    duration_ms: int = 0
    disclosures: list[str]

