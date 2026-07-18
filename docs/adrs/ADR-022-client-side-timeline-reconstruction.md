# ADR-022: Client-side timeline reconstruction

- Status: Proposed
- Date: 2026-07-18

## Context

`RepresentativeRunResult.result.events` already contains the complete ordered sampled-event log for a bounded set of selected items (`resultDetail.selectedItemIds`, sampled limit 25 by default). Reconstructing playback frames (queue state, resource usage, item state) from those events is a deterministic, pure function of the event list. Nothing about frame reconstruction requires new backend execution.

## Options considered

### Option A — Server-computed frames, one request per seek

Correctness is easy to centralize, but adds request latency to every scrub/step, couples the UI to a new endpoint, and does not fit "no server streaming."

### Option B — Server streams a WebSocket of live frames

Explicitly out of scope (no live simulation streaming, no WebSockets) and misrepresents a static retained run as a live process.

### Option C — Client-side pure reconstruction from the existing retained event array

No new backend contract, no network round trip per interaction, deterministic and testable in isolation, and bounded by the same sampled-event volume the product already returns.

## Decision

Choose Option C. Playback frames are reconstructed entirely client-side from the retained representative's `events` array. No event semantics are duplicated or reinterpreted on the server; the frame-reconstruction function only re-derives *presentation* state (stage/resource/item occupancy at a point in time) from the same event vocabulary already defined in `EventType`.

## Consequences

- No server streaming, no new WebSocket, no new playback-specific backend route.
- Reconstruction must be deterministic: the same normalized events and the same requested time always produce the same frame (GM-131 seek determinism).
- Payload stays bounded by the existing sampled-event retention limit; playback does not request `full` detail mode by default and never triggers a second simulation execution.
- The event ledger is the accessible, complete non-visual equivalent of every reconstructed frame (no information is only available through animation).
- Precomputed time-grouped indexes and periodic checkpoints keep interactive seek/step bounded instead of replaying from event zero on every tick (see `REPRESENTATIVE_PLAYBACK_SPEC.md` — Frame reconstruction).
- Revisit trigger: if the retained sampled-event limit is ever raised by an order of magnitude, checkpoint density and memory bounds must be re-measured (`pnpm benchmark:playback`).

Mark accepted after implementation and the Sprint 10 tests pass.
