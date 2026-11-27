# Synthetic operational laboratory

Two evaluation sources stay distinct:

1. **Offline seeded fixtures** (`generateSynthetic`) for normalization, quality, and future calibration holdouts. Profiles: `golden`, `medium`, `stress`, `known-process`.
2. **Live Jira sandbox** (`scripts/jira-sandbox-fixtures.mjs`) for connector authorization only. Allowlist: `opstwin-dev.atlassian.net` / `OPS`. Dry-run default. Max 8 issues. Label `opstwin-synthetic`.

Jira Cloud stamps current timestamps. Rapidly created live issues are not months of history. Do not execute `--execute` without owner approval.
