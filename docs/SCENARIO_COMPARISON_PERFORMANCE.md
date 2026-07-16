# Scenario Comparison Performance

## Scope

This local engineering baseline measures the required sequential Sprint 04 matrix. It is not hosting or Vercel compatibility evidence. Every ordinary simulation used summary detail; only sampled baseline and selected-scenario representatives returned events.

## Environment

- Date: 2026-07-16
- Platform: Windows 11 `10.0.26200`
- Python: 3.12.13
- Base seed: 20250715
- Representative detail: sampled, limit 25
- Execution: sequential, no workers or parallelism

## Results

| Items | Runs | Scenarios | Variants | Work units | Ordinary | Reps | Seconds | Mean sim (s) | Events | Comparison bytes | Baseline rep bytes | Scenario rep bytes | Valid/failed | Min paired | Max retained | Integrity |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| 100 | 10 | 2 | 3 | 3,000 | 30 | 2 | 0.617941 | 0.018986 | 25,600 | 152,359 | 51,939 | 52,039 | 2/0 | 1.0 | 2 | passed |
| 100 | 100 | 2 | 3 | 30,000 | 300 | 2 | 5.073717 | 0.016672 | 241,600 | 161,269 | 51,939 | 52,039 | 2/0 | 1.0 | 2 | passed |
| 1,000 | 10 | 2 | 3 | 30,000 | 30 | 2 | 6.384422 | 0.198661 | 256,000 | 153,874 | 52,630 | 52,728 | 2/0 | 1.0 | 2 | passed |
| 100 | 50 | 5 | 6 | 30,000 | 300 | 2 | 7.053617 | 0.023117 | 241,600 | 215,784 | 51,939 | 52,042 | 5/0 | 1.0 | 2 | passed |

`Events` is total generated event count across ordinary and representative executions. Each case returned 400 sampled representative events.

## Synchronous work guard

Estimated work is `baseline item count × run count × total model variants` and is checked before materialization or simulation. The limit is 100,000 item executions. The required matrix reaches 30,000 and completed locally in under eleven seconds per case; the larger limit is an engineering guard with headroom, not a production capacity claim. Requests above it return a safe structured rejection.

## Interpretation

All scenarios succeeded, every paired ratio was 1.0, and comparison integrity passed. Aggregate payload size grew with run diagnostics and scenario count while representative payloads stayed bounded by sampled detail. Maximum simultaneously retained event-rich results was two in every case.
