# ADR-025: Canonical operational snapshots stay outside Core

- Status: accepted
- Date: 2026-11-27

## Context

CG-2 must turn authorized Jira/JSM records into inspectable operational evidence without calibrating a simulation model or sending issue payloads to the existing FIT remote.

## Decision

1. **Boundary.** Canonical types live in `contracts/operational-snapshot.schema.json` (`os.1.0.0`). Jira field names exist only in `apps/atlassian-forge/src/jira/`. Normalization, quality, and descriptive evidence live in `apps/atlassian-forge/src/operational/` and do not import `@forge/*`.
2. **Import execution.** Bounded synchronous resolver import (40 cases, 8 pages, 20s deadline, 30/60/90-day windows). Changelog completeness is taken from `/issue/{key}/changelog` pagination, not from a nonempty search `expand=changelog`. Asynchronous Forge events are deferred until a measured workload exceeds the UI budget.
3. **Persistence.** Snapshots are returned on the resolver response and held in Custom UI session state. No extra database and no `storage:app` scope in CG-2. Failed imports clear the current snapshot.
4. **Authorization.** Project identity comes from Forge extension context. Retrieval uses `api.asUser()`. Browser `projectKey` cannot select another project. Installation identity is recorded for provenance and is not treated as project authorization.
5. **Time.** Observation windows are closed-start, open-end UTC. Status residence, elapsed lifetime, recorded work, and SLA elapsed time are separate interval types. Negative durations are rejected. Missing history is incomplete/unknown, never invented.
6. **Synthetic data.** Offline seeded generators produce historical fixtures. Live sandbox issue creation is a dry-run allowlisted tool only. Live transport does not change synthetic origin labels.

## Consequences

- Core simulation contracts remain `0.2.0`–`0.7.0`.
- `POST /api/integrations/atlassian/v1/compare` stays synthetic-only.
- Reload of the Jira page drops the in-session snapshot until a later persistence ADR.
