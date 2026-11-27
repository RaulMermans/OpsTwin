# Calibration architecture

Snapshot (`os.1.0.0`) → eligibility/mapping → identifiability → estimation/assumptions → Core model (`0.2.0`) → bounded simulation → generative holdout report (`cal.1.0.0`).

The calibration package must not import Forge. Core must not import calibration remotes. FIT compare stays synthetic-only.

Selected model class: `support-triage-resolution.1`. Engine distributions: Poisson arrivals; exponential processing for CG-3 estimates; FIFO; no calendars; empty initial system. Canonical constructed models use `itemCount=1` as a rate-model placeholder; validation copies set the execution cap. Model identity excludes that cap and the simulation seed schedule.

Rejected alternatives: duplicating the simulator in JavaScript; fitting gamma/lognormal unsupported by Core; treating changelog residence as busy time; sending live snapshots to `/compare`.
