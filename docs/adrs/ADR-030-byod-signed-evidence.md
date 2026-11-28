# ADR-030: Bring-your-own-data baselines and signed operational evidence

- Status: accepted
- Date: 2026-11-27

## Context

CG-7 must let users analyze their own operations inside Jira without a second simulation engine, and must stop treating browser-supplied experiment metrics as authoritative financial inputs.

## Decision

1. All source modes (synthetic fixture, manual parameters, minimized Jira snapshot, CSV event log) construct the existing `support-triage-resolution.1` model through `calibrate()` or `construct_manual_artifact()`.
2. Manual models are `user_defined_exploratory`. Jira/CSV models are `source_linked_exploratory` until holdout validation independently passes.
3. The simulation remote signs baseline and experiment artifacts with an HMAC key held only in server environment variables (`OPSTWIN_EVIDENCE_HMAC_KEY`). Tokens bind application, environment, installation, project, principal (or `scope:installation-user-context`), purpose, and artifact type. Economic evaluation verifies those bindings before arithmetic. Existing ev1 tokens without project/principal fail bind after CG-7.1 (6-hour TTL).
4. Jira observed records are extracted by the Forge resolver (`api.asUser()`). Browser snapshots are not trusted Jira evidence. Baseline tokens reconstruct from a compact signed model, not an embedded operational history.
5. Realizable cash is withheld when modeled period processing exceeds staffed paid hours. Avoided-hiring cash that exceeds current payroll is labeled as future-expenditure assumption, not a current payroll cut.
6. Fixed-workload economics do not annualize finite experiments. Recurring-period economics require expected monthly demand and apply linear per-case scaling, with ROI/payback withheld when that basis is missing.
7. Break-even exploration requires an explicit strategy. AI subscription sensitivity is rejected for strategies that do not use AI.

## Consequences

- Minimized operational snapshots may leave Forge for calibration. Descriptions, comments, attachments, and personal names stay excluded.
- A valid signature does not replace FIT, installation, or project authorization.
- Local mocked isolation tests are not multi-installation acceptance.
