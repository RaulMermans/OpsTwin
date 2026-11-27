# ADR-029: Decision economics reuse the existing cost engine without a second model

- Status: accepted
- Date: 2026-11-27

## Context

CG-6 must connect operational experiments to ROI, payback, cash-versus-capacity, and break-even without inventing a second simulation or finance platform. ADR-019 forbids inferred money and does not compute ROI. CG-5 experiments drain a finite workload until empty, so scenario-specific horizons make throughput, utilization, and resource-provisioning cost incomparable.

## Decision

1. Keep `0.7.0` cost snapshots for Core economics. Jira decision evaluation (`cg6.v1`) is a deterministic overlay on validated `cg5.v1` evidence.
2. Measurement mode for Codegeist experiments is **fixed workload** (finite Poisson arrivals, drain until empty). Completions and item cycle times are comparable. Throughput, utilization, and time-dependent provisioning costs are disclosed as duration-dependent and are not cash denominators.
3. Staffing cash is calendar payroll (`FTE × monthly loaded cost × evaluation months`), not simulated busy minutes. Released busy hours are capacity, not cash, unless an explicit realization mechanism and rate are supplied.
4. ROI = net benefit / incremental investment, with net benefit = realizable cash − incremental investment. ROI is omitted when the investment denominator is zero. Payback exists only when cumulative incremental cash recovers one-time implementation within the evaluation horizon.
5. Financial-only break-even reuses the same operational means. Parameters that change queue behavior require another comparison experiment.
6. Remote `POST /api/integrations/atlassian/v1/evaluate-economics` stays FIT-authenticated. CG-7 requires a server-signed evidence token rather than browser-supplied metrics (ADR-030).

## Consequences

- AI is not preferred by construction; negative net benefit is a supported outcome.
- Economic uncertainty is labeled conditional on summarized operational outcomes, not a Monte Carlo ROI interval.
- Source-linked live calibration remains a CG-7 item.
