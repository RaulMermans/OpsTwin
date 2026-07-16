# Sprint 00 Foundation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task using test-driven development for observable behavior. Do not commit or push.

**Goal:** Establish a runnable monorepo foundation and prove a deterministic service-operations simulation with hand-calculated tests.

**Architecture:** A minimal Next.js TypeScript frontend is separated from a FastAPI/SimPy Python service. Implementation-neutral JSON Schemas define input and output boundaries; a normalized event log is the canonical simulation evidence.

**Tech stack:** Next.js, TypeScript, pnpm, FastAPI, Pydantic, SimPy, pytest, Ruff, mypy, JSON Schema, and optional Make compatibility.

## Scope

- Repository controls, documentation, scoped Claude rules, and local skills.
- Deterministic source-to-FIFO-to-stage simulation only.
- Minimal foundation page and health endpoint.
- Contracts, exact tests, CLI, CI, and root verification commands.

## Tasks

- [x] Create controls, specifications, ADRs, contracts, and the example model.
- [x] Write failing API, validation, schema, and simulation tests.
- [x] Implement the minimal Python service and deterministic engine until tests pass.
- [x] Add the minimal accessible Next.js foundation page.
- [x] Add workspace commands, lockfiles, and CI.
- [x] Run all available quality gates, review the diff and scans, and update the scratchpad.

## Acceptance criteria

- `CLAUDE.md` is below 200 lines; four accepted ADRs and all required specifications exist.
- Scoped rules and three local skills have valid YAML frontmatter.
- Web and API applications start without external services.
- The example validates, produces exact hand-calculated metrics, and repeats identically.
- Web/Python lint, TypeScript/Python typecheck, tests, builds, and the cross-platform `pnpm verify` gate pass.
- No deferred product features or infrastructure are introduced.

## Definition of done

All acceptance criteria are verified, documentation and scratchpad match implementation, and Git contains only intended uncommitted Sprint 00 changes.
