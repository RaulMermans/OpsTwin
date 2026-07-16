# ADR-008: Result-detail modes

- Status: accepted

## Context

Full event logs grow rapidly, while future Vercel-bound synchronous responses need bounded payloads. Full evidence remains useful for tests/debugging, and future playback needs a representative compact subset.

## Options considered

### Option A — Always return full events

Preserves all evidence but produces unbounded response growth.

### Option B — Return metrics only

Bounds responses but loses debugging and representative playback evidence.

### Option C — Explicit summary, sampled, and full modes

Preserves one metric contract while allowing callers to select evidence volume.

## Decision

Simulation responses support `summary`, `sampled`, and `full` detail modes while preserving identical core metrics.

## Consequences

- `summary` returns metrics and counts without event records.
- `sampled` returns metrics and all events for a deterministic item subset.
- `full` returns the complete canonical event log.
- Total and included event counts are separate.
- Sample IDs are chosen before simulation without consuming run-generator draws; event retention occurs at emission.

## Sampling rule

Compute SHA-256 from `seed:itemId`, rank item IDs lexically by digest then ID, select the lowest ranks up to the requested limit, include every event for those items, and preserve original event ordering.

## Revisit triggers

- Playback requires cross-item system events not associated with item IDs.
- Payload limits require compression or external durable storage.
- Contract consumers require paginated full evidence.

## Validation plan

Assert identical core metrics and total event counts across modes, deterministic selected IDs, zero summary events, complete full events, and unchanged subsequent stochastic samples.

## 2026-07-15 clarification: internal retention

Result detail governs both returned payload and internal event-object retention. Every canonical event updates a compact audit ledger and streaming observation collector, but only requested event objects remain after emission:

- `summary`: compact ledger and observation state; zero retained events.
- `sampled`: compact ledger and observation state plus events for item IDs selected before execution by the accepted stable-hash rule.
- `full`: compact ledger and observation state plus every canonical event.

The ledger preserves integrity checks and total event counts for all modes. Preselection uses predictable source item IDs and does not consume the simulation RNG. This clarification changes retention, not the original public result contract or sampling order.
