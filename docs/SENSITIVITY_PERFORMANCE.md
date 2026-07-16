# Sensitivity Performance

## Benchmark contract

Run `pnpm benchmark:sensitivity` locally. The matrix is 100 items × 10 runs × 3 values, 100 × 50 × 5, 100 × 100 × 5, and 1,000 × 10 × 3. Each case reports work units, ordinary executions, elapsed seconds, payload bytes, returned-event count, and integrity status. `pnpm verify` uses only the 10 × 2 × 2 smoke case.

## Interpretation

Measurements describe this local machine and process only; they are not hosting-capacity claims. Work is bounded before simulation, ordinary results retain no events, and runtime is expected to scale primarily with item executions. Final measured values are recorded in the Sprint report after the one permitted benchmark attempt.

## 2026-07-16 local measurement

Environment: Windows 11 `10.0.26200`, Python `3.12.13`.

| Items | Runs | Values | Work units | Ordinary executions | Seconds | Payload bytes | Paired ratio | Integrity | Returned events |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 100 | 10 | 3 | 3,000 | 30 | 0.834 | 12,179 | 1.0 | passed · 24 checks | 0 |
| 100 | 50 | 5 | 25,000 | 250 | 4.813 | 22,691 | 1.0 | passed · 24 checks | 0 |
| 100 | 100 | 5 | 50,000 | 500 | 12.520 | 24,966 | 1.0 | passed · 24 checks | 0 |
| 1,000 | 10 | 3 | 30,000 | 30 | 7.194 | 12,181 | 1.0 | passed · 24 checks | 0 |

These are single local observations, not service-level guarantees.
