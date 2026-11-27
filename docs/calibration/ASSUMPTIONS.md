# Assumptions

Material assumptions are inspectable records: parameter, proposed value, unit, evidence available, why required, plausible range, operational consequence, approval, revision.

No autonomous approval. Synthetic fixtures do not approve assumptions by default. Interactive calibration requires an explicit acceptance checkbox. `allowAssumptionBasedModel` must be true when approved assumptions bind the model.

Changing an approved value changes `contentIdentity` and `modelFingerprint` and drops previous validation.

Units, finite numbers, positive processing durations, integer staffing, ranges, identifier consistency, and unknown-parameter refusal are enforced. Fractional capacity is not truncated to an integer. Arbitrary strings are not parsed as numbers.

Defaults exist only as labeled laboratory proposals (`source: synthetic-spec` or analyst). They are not fitted distributions. The naive benchmark baseline is **estimated arrivals with default service/capacity**, not an uncalibrated model.
