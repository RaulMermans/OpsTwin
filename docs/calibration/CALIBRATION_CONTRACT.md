# Calibration contract `cal.1.0.0`

Pydantic models in `apps/simulation-api/app/calibration/contracts.py`.

- `CalibrationRequest`: snapshot fingerprint, mapping, assumption set, windows, seed, budgets, recorded thresholds.
- `ParameterEstimate`: value, unit, method, **evidence class** (separate from method), identifiability, sample size, uncertainty.
- `AssumptionRecord`: proposed value, range, approval, revision. Unapproved records cannot become model parameters.
- `CalibrationArtifact`: estimates, assumptions, constructed model, content identity (immutable) vs `executionMetadata` (volatile).
- `CalibrationValidationReport`: generative mode, per-target outcomes, failed gates. Not the comparison `0.5.0` contract.

Readiness is a lifecycle, not a boolean: `insufficient_evidence`, `mapping_required`, `assumptions_required`, `model_constructed`, `validation_pending`, `validation_failed`, `validated_for_defined_scope`.
