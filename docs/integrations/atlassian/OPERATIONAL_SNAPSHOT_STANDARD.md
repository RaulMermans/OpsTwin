# Operational snapshot standard (`os.1.0.0`)

An operational snapshot is a versioned, inspectable record of observed demand. It is not an operational model (`0.2.0`) and it is not calibrated.

## Identity

- `snapshotId` identifies one import instance (includes import time material).
- `contentFingerprint` is SHA-256 of canonical JSON over schema, connector, source, window, import configuration, cases, events, statuses, request types, and intervals.
- Volatile fields excluded from the fingerprint: `snapshotId`, `importTimestamp`, `importStartedAt`, `importCompletedAt`, `extractionTimestamp`, `observedAt`.

## Cohort

`open-during-window`: `created < window.end AND (resolved IS EMPTY OR resolved >= window.start)` with `closed-start-open-end-utc`.

## Evidence classes

`observed`, `derived`, `assumed`, `synthetic`, `unknown`. CG-2 emits observed/derived from live APIs and synthetic from fixtures. Live retrieval of labeled synthetic Jira issues stays `synthetic` for origin and `live_api` for transport.

## Readiness

`valid`, `partial`, `invalid`, `insufficient_for_calibration`, `potentially_suitable_for_calibration_assessment`. Never `calibrated` or `simulation-ready`.
