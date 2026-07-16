# Repeated-Run Performance Baseline

## Scope and method

This local engineering baseline uses `pnpm benchmark:repeated`. Each ordinary run uses summary evidence; one representative seed is rerun in sampled mode with limit 25. Timings use `time.perf_counter`. Aggregate payload is the complete repeated response; representative payload is the nested single-run contribution. Results are not hosting-capacity claims.

## Environment

- Recorded: 2026-07-15
- OS: Windows 11 (`Windows-11-10.0.26200-SP0`)
- CPU: Intel Core i3-10100, 4 cores / 8 logical processors
- Memory: 7.65 GiB
- Python: 3.12.13
- Node.js: 24.14.0
- pnpm: 11.7.0
- Base seed: 20250715

## Measurements

| Items/run | Runs | Execute (s) | Mean ordinary (s) | Generated events | Aggregate bytes | Representative bytes | Returned events | Max retained results | Integrity |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| 100 | 10 | 0.311469 | 0.028001 | 8,800 | 61,855 | 51,939 | 200 | 1 | passed |
| 100 | 100 | 3.285230 | 0.032310 | 80,800 | 67,185 | 51,939 | 200 | 1 | passed |
| 1,000 | 10 | 4.563394 | 0.417297 | 88,000 | 62,579 | 52,630 | 200 | 1 | passed |
| 1,000 | 50 | 17.003714 | 0.331869 | 408,000 | 65,221 | 52,630 | 200 | 1 | passed |

All workloads completed with zero failed runs. Payload growth is driven mainly by seed lists, convergence checkpoints, and aggregate metadata rather than ordinary event histories. Full event evidence is never retained across ordinary runs; one representative result remains in the response.

## Commands

- Full matrix: `pnpm benchmark:repeated`
- Smoke included in repository/CI verification: `pnpm verify`

Re-record when run contracts, snapshot fields, event cardinality, retention, aggregation, Python/SimPy versions, or hardware materially change.
