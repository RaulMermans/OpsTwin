# Statistical methods (CG-3)

Arrival: homogeneous Poisson MLE. Mean interarrival = training exposure / created count. Rate interval uses a normal approximation to the Poisson count. Not implemented: time-varying Poisson, renewal forecasting.

Service: mean of complete, attributed, in-window **processing episodes** (merged adjacent/overlapping worklogs on the same case and stage). Unattributed worklogs stay unattributed. A Boolean usage flag is not completeness. Boundary-crossing worklogs are censored and do not contribute full duration. Status residence is never used. Uncertainty is a Student-t interval on the episode mean, not 0.5×/1.5× the mean.

Routing: empirical shares on mapped, complete training transitions when sample size meets the configured minimum. Sparse competing routes stay unknown (not zero). Unsupported transitions refuse the model. If no competing route is observed, probability 1 is recorded as a **structural linear-template constraint**. Reopening is not failure probability.

Capacity: approved integer servers only. Fractional values are refused, not truncated.

Holdout: predefined time fraction of the snapshot window (not a cut chosen from future arrival counts). Training-only estimation. Generative validation uses `maxReplications` (default 3) with SHA-256-derived simulation seeds distinct from the fixture seed. Cycle-time percentiles require pre-registered minimum sample sizes (10 / 20). Empty Core initial conditions are incompatible with historical WIP; arrival-only comparison may remain eligible. Truncated item caps cannot claim arrival-process adequacy.

Candidate processing distributions in Core: fixed, exponential, uniform, triangular. CG-3 emits exponential when a mean is identified or assumed.

Thresholds for synthetic development (not industry standards): arrival/throughput 15%, cycle median 20%, p90 25%. Recorded on the request before evaluation.
