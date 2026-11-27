# Data quality standard (CG-2)

Each quality result has `metricId`, `definition`, numerator, denominator, `value`, `status` (`pass` | `warning` | `fail` | `unknown` | `not_applicable`), `explanation`, `consequence`, and `recommendedNextAction`.

| metricId | Meaning |
|---|---|
| completeness | Valid created timestamps |
| validity | Absence of invalid timestamps |
| consistency | Events do not precede creation; negative intervals unknown |
| uniqueness | Deduplicated case identities |
| temporal_coverage | Configured window versus 90-day reference |
| lifecycle_coverage | Status history reconstructable |
| worklog_coverage | Cases with recorded work |
| sla_coverage | Cases with SLA cycles |
| classification_coverage | Request type and status present |
| representativeness | Extraction finished inside budgets |
| authorization_coverage | User-context project authorization |

No composite score is published. Missing evidence is not an assumed zero.
