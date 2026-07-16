# ADR-010: Online aggregation and representative rerun

- Status: accepted

## Context

Full event logs multiply memory and payload cost across runs. Aggregate statistics need scalar metrics, future playback needs one representative run, and auditability requires explicit seeds and failure evidence.

## Options considered

### Option A — Retain every full simulation result

Maximizes evidence but violates bounded retention.

### Option B — Aggregate online and retain no representative evidence

Bounds memory but cannot support representative inspection or future playback.

### Option C — Aggregate compact snapshots and rerun one representative seed

Bounds ordinary retention while preserving one reproducible evidence result.

## Decision

Ordinary runs execute in summary mode, retain only scalar snapshots, aggregate sequentially, and rerun one median-vector representative seed with bounded configured detail.

## Consequences

Complete ordinary results are released; scalar snapshots may remain through selection; only one representative result is returned; execution is sequential; and representative evidence costs one additional run.

## Revisit triggers

Run caps exceed scalar memory, approximate streaming quantiles become necessary, distributed workers appear, or multiple representatives are required.

## Validation plan

Assert ordinary summary detail, no ordinary retained events, maximum one live single-run result, exact representative snapshot reproduction, and one representative rerun.
