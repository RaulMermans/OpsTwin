# Identifiability

Evaluated against available evidence and the selected template, not against the ability to emit a number.

| Parameter | Identifiable when | Refused when |
|---|---|---|
| Arrival rate | Enough valid created timestamps in the training window | Coverage too small; homogeneous Poisson split-shift > 0.75 |
| Demand mix | Request types present | Diagnostic only (single arrival class) |
| Routing | Mapped complete transitions with sufficient sample size | Unsupported, sparse competing, or unknown routes (never probability zero) |
| Service time | Complete attributed worklog **episodes**, completeness evidence, explicit treatment flag | Status residence; unattributed, overlapping, invalid, or censored worklogs |
| Capacity | Never from assignees | Assignee counts |
| Rework | Never from reopen events | Reopen frequency |
| Queue discipline / calendar | Explicit assumption | Observed timestamps alone |

States: `identifiable`, `partially_identifiable`, `assumption_required`, `not_identifiable`, `insufficient_evidence`.
