# ADR-030: Bring-your-own-data baselines and signed operational evidence

- Status: accepted
- Date: 2026-11-27

## Context

CG-7 must let users analyze their own operations inside Jira without a second simulation engine, and must stop treating browser-supplied experiment metrics as authoritative financial inputs.

## Decision

1. All source modes (synthetic fixture, manual parameters, minimized Jira snapshot, CSV event log) construct the existing `support-triage-resolution.1` model through `calibrate()` or `construct_manual_artifact()`.
2. Manual models are `user_defined_exploratory`. Jira/CSV models are `source_linked_exploratory` until holdout validation independently passes.
3. The simulation remote signs baseline and experiment artifacts with an HMAC key held only in server environment variables (`OPSTWIN_EVIDENCE_HMAC_KEY`). Economic evaluation verifies the token and installation/app/environment binding before arithmetic.
4. Fixed-workload economics do not annualize finite experiments. Recurring-period economics require expected monthly demand and apply linear per-case scaling, with ROI/payback withheld when that basis is missing.
5. Break-even exploration requires an explicit strategy. AI subscription sensitivity is rejected for strategies that do not use AI.

## Consequences

- Minimized operational snapshots may leave Forge for calibration. Descriptions, comments, attachments, and personal names stay excluded.
- A valid signature does not replace FIT, installation, or project authorization.
- Local mocked isolation tests are not multi-installation acceptance.
