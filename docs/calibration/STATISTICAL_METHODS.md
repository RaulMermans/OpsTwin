# Statistical methods (CG-3)

Arrival: homogeneous Poisson MLE. Mean interarrival = training exposure / created count. Rate interval uses a normal approximation to the Poisson count. Not implemented: time-varying Poisson, renewal forecasting.

Service: mean of complete, uncensored, non-overlapping `recorded_work` intervals only when `treatWorklogsAsProcessing` is explicit. Otherwise exponential means come from approved assumptions. Status residence is never used. Censoring: incomplete durations are excluded and counted, not treated as zero.

Routing: empirical shares on mapped, complete training transitions. No additive smoothing. Unsupported transitions refuse the model. Reopening is not failure probability.

Capacity: approved integer servers only.

Candidate processing distributions in Core: fixed, exponential, uniform, triangular. CG-3 emits exponential when a mean is identified or assumed.

Thresholds for synthetic development (not industry standards): arrival/throughput 15%, cycle median 20%, p90 25%. Recorded on the request before evaluation.
