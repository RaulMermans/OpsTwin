# Calibration contract `cal.1.0.0`

Pydantic models in `apps/simulation-api/app/calibration/contracts.py`.

- `CalibrationRequest`: snapshot fingerprint, mapping, assumption set, windows, seed, budgets, recorded thresholds.
- `ParameterEstimate`: value, unit, method, **evidence class** (separate from method), identifiability, sample size, uncertainty.
- `AssumptionRecord`: proposed value, range, approval, revision. Unapproved records cannot become model parameters.
- `CalibrationArtifact`: estimates, assumptions, constructed model, `modelFingerprint`, `contentIdentity`, `executionIdentity`. `consumedByModel` and `origin` distinguish empirical, assumed, structural, and diagnostic parameters.
- Engine version `cg3.1.cal.1`. Snapshot validation uses `os.1.0.0` JSON Schema plus semantic identity/interval/provenance checks.
- `CalibrationValidationReport`: generative mode, per-target outcomes, failed gates. Not the comparison `0.5.0` contract.

Readiness is a lifecycle, not a boolean: `insufficient_evidence`, `mapping_required`, `assumptions_required`, `model_constructed`, `validation_pending`, `validation_failed`, `validated_for_defined_scope`.
