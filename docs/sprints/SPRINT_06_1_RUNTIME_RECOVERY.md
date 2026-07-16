# OpsTwin Sprint 06.1 — Runtime Verification Recovery and Scenario Lab Hardening

## Objective

Recover as much local verification evidence as the current Windows runtime permits, preserve the Sprint 06 Scenario Lab contracts, and distinguish product defects from environment-level process and temporary-directory failures before Sprint 07 begins.

## Inherited environment blockers

- The bundled `pnpm` launcher is available, but its child `node` executable is not discoverable through the normal process `PATH`.
- The portability probe reaches `spawnSync` and receives a `null` status rather than a successful child-process exit.
- Python package setup cannot create or enter pip build-tracker directories beneath the configured user temporary root.
- Existing pytest temporary roots are inaccessible. They are evidence, not cleanup targets.
- The environment does not permit changing permissions, patching runtime tooling, or relocating test output into tracked source directories.

## Initial preflight evidence

The required root preflight commands were each attempted once and will not be retried without an environment change.

| Command | Result | Classification |
| --- | --- | --- |
| `pnpm bootstrap` | Failed while pip attempted to use an inaccessible build-tracker directory; the fallback then could not resolve `node`. | Environment blocked |
| `pnpm verify` | Failed in `scripts/verify-node-portability.mjs` because the spawned process returned status `null`; the fallback then could not resolve `node`. | Environment blocked |

## Verification strategy

1. Attempt each required targeted root command exactly once: web tests, lint, typecheck, and build.
2. If a root command is blocked by the inherited launcher/process environment, use the repository's installed package tools through the known bundled Node executable.
3. Run the simulation API test suite once through the repository virtual environment.
4. Attempt the local web runtime once. Perform browser verification only if the server becomes reachable.
5. Fix only reproducible source defects. Do not weaken assertions or checks to convert environment failures into passes.
6. Record each gate as passed, failed, partial, or blocked from executed evidence only.

## Scope

- Local runtime verification recovery.
- Scenario Lab type, lint, unit-test, build, API-test, and browser evidence.
- Source-level fixes for defects reproduced by those checks.
- Validation-plan and scratchpad reconciliation.

## Out of scope

- Deployment, Vercel, GitHub, remote CI, commits, staging, or pushes.
- Permission changes, deletion of inaccessible temporary directories, or runtime-tool patching.
- Product-contract changes, backend mathematics changes, and verification bypasses.

## Acceptance criteria

- Root bootstrap and verification attempts are documented without unchanged retries.
- Targeted verification commands are attempted and classified.
- Package-local alternatives are used where they provide independent evidence.
- Any reproducible Scenario Lab source defect is fixed and rechecked proportionally.
- GM053–GM068 are reconciled only against executed evidence.
- The repository remains local-only and deployment-neutral.

## Definition of done

- The verification matrix contains commands, outcomes, and blocker ownership.
- Source-level verification is as complete as the environment permits.
- Runtime/browser gaps remain explicit rather than inferred as passes.
- Sprint 07 may begin without claiming that blocked Sprint 06 gates passed.

## Rollback

Sprint 06.1 documentation and any narrowly scoped Scenario Lab fixes can be reverted independently. No environment, permission, dependency, backend-contract, or deployment mutation is part of this sprint.
