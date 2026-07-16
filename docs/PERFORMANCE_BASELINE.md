# Simulation Performance Baseline

## Scope and method

This is a local engineering baseline, not a production capacity or Vercel-safety claim. `pnpm benchmark:simulation` runs a fixed-seed, one-stage deterministic model with arrival interval `1`, processing duration `0.5`, capacity one, and eight canonical events per item. It measures engine execution and JSON serialization separately with `time.perf_counter`, records UTF-8 payload bytes, and requires integrity validation to pass.

## Environment

- Recorded: 2026-07-15
- OS: Windows 11 (`Windows-11-10.0.26200-SP0`)
- CPU: Intel Core i3-10100, 4 cores / 8 logical processors
- Memory: 7.65 GiB
- Python: 3.12.13
- Node.js: 24.14.0 (workspace bundled runtime)
- pnpm: 11.7.0
- Seed: 20250715

## Measurements

| Items | Detail | Included events | Total events | Execute (s) | Serialize (s) | Payload bytes |
|---:|:---|---:|---:|---:|---:|---:|
| 100 | summary | 0 | 800 | 0.031963 | 0.000131 | 1,661 |
| 100 | full | 800 | 800 | 0.043826 | 0.005619 | 201,405 |
| 1,000 | summary | 0 | 8,000 | 0.729641 | 0.000178 | 1,677 |
| 1,000 | full | 8,000 | 8,000 | 0.392035 | 0.037860 | 2,022,830 |
| 10,000 | summary | 0 | 80,000 | 3.400961 | 0.000205 | 1,691 |
| 10,000 | full | 80,000 | 80,000 | 4.530591 | 0.229476 | 20,452,853 |
| 10,000 | sampled, limit 25 | 200 | 80,000 | 3.798197 | 0.001114 | 53,266 |

Execution times naturally vary by host load. The durable observations are that summary serialization and payload remain bounded, sampled evidence is bounded by selected item histories, and full payload scales with canonical event count. Every mode audits and observes all canonical emissions; only full mode constructs and retains all event objects.

## Sprint 02.1 retention hardening

A separate 1,000-item `tracemalloc` diagnostic compared the former full internal event list with emission-time retention. These are diagnostic observations rather than the command matrix above; shallow bytes measure the retained event-list objects only.

| Mode | Before retained events | After retained events | Before traced peak bytes | After traced peak bytes |
|:---|---:|---:|---:|---:|
| summary | 8,000 | 0 | 13,426,416 | 3,070,441 |
| sampled, limit 25 | 8,000 | 200 | 13,410,810 | 3,251,595 |
| full | 8,000 | 8,000 | 13,410,754 | 13,359,254 |

Summary retained-event shallow size fell from 643,224 bytes to 56 bytes; sampled retained-event shallow size fell from 643,224 bytes to 16,056 bytes. Full mode intentionally remains proportional to complete evidence.

## Commands

- Full baseline: `pnpm benchmark:simulation`
- CI/repository smoke: `pnpm verify` invokes the benchmark with `--smoke`

Re-record this file when simulator algorithms, event cardinality, integrity checks, Python/SimPy versions, or benchmark hardware materially change.
