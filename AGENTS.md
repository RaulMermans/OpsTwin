# OpsTwin project control

## Product

OpsTwin is a digital twin-style environment for simulating business operations and evaluating operational decisions. The initial wedge covers customer support, claims, onboarding, and back-office requests. Maturity: prototype moving toward MVP.

## Priorities

1. Simulation correctness
2. Reproducibility
3. Explainability
4. Minimal architecture
5. Visual quality after mathematical validity

## Non-negotiables

- Read the current sprint document before editing.
- Read relevant Markdown specifications before implementing.
- Do not invent simulation semantics or silently change metric definitions.
- Do not add dependencies without justification.
- Do not modify architecture without an ADR.
- Keep changes bounded to the active sprint.
- Never store secrets.
- Use deterministic seeds in tests when randomness exists.
- Every behavior change requires an executable verification path.
- Do not build UI ahead of validated engine capabilities.

See `docs/sprints/SPRINT_04_SCENARIO_COMPARISON.md`, `docs/SCENARIO_COMPARISON_SPEC.md`, and `docs/METRIC_DEFINITIONS.md` for Core simulation semantics.

Atlassian/Codegeist work is an additional isolated track. Read `docs/codegeist/sprints/CG-00.md`, `docs/codegeist/sprints/CG-01.md`, `docs/adrs/ADR-023-atlassian-application-isolation.md`, and `docs/adrs/ADR-024-forge-remote-python-adapter.md` before editing `apps/atlassian-forge/`, `apps/simulation-api/app/integrations/`, or `docs/integrations/atlassian/`. OpsTwin Core must never import Forge or Atlassian modules. Do not register, deploy, or install a Forge app without owner authentication on `opstwin-dev.atlassian.net`.

Durable integration rules:

- Never classify a malformed successful API response as an empty dataset.
- Never treat optional JWT expiration validation as sufficient when expiration is mandatory.
- Never infer project authorization from installation identity alone.
- Never claim hosted integration success based on local mocks.
- Never exclude entire directories from security scans without justified, reviewed exceptions.
- Missing operational evidence must never become an assumed zero.
- Jira status residence time must never be treated automatically as active service time.
- Live transport does not establish genuine historical data origin.
- Valid snapshots require explicit completeness and provenance.
- Partial extraction must never be presented as complete.
- Tenant and project authorization are separate concerns.
- Snapshot fingerprints must be reproducible.
- Calibration must remain distinct from ingestion.
- Every calibrated parameter requires inspectable provenance.
- Identifiability is evaluated before estimation.
- Missing evidence never silently becomes a numerical assumption.
- Status residence is not automatically service time.
- Holdout observations cannot influence parameter fitting.
- Historical validation does not establish causal intervention validity.
- Synthetic recovery benchmarks do not prove real-world accuracy.
- Material assumption changes invalidate dependent validation.

Read `docs/codegeist/sprints/CG-02.md`, `docs/codegeist/sprints/CG-03.md`, `docs/adrs/ADR-025-canonical-operational-snapshots.md`, and `docs/adrs/ADR-026-operational-calibration-layer.md` before changing operational ingest, snapshots, or calibration.

## Context discipline

- Read only relevant files and prefer targeted searches.
- Do not import all documentation at session startup.
- Keep one conversation focused on one sprint or bounded task.
- Use `/compact` when context becomes noisy.
- Update `SCRATCHPAD.md` before ending significant work.

## Standard commands

- Bootstrap: `pnpm bootstrap`
- Web development: `pnpm dev:web`
- API development: `pnpm dev:api`
- Example simulation: `pnpm run-example`
- Full simulation benchmark: `pnpm benchmark:simulation`
- Repeated simulation benchmark: `pnpm benchmark:repeated`
- Scenario comparison benchmark: `pnpm benchmark:comparison`
- Lint: `pnpm lint`
- Typecheck: `pnpm typecheck`
- Test: `pnpm test`
- Build: `pnpm build`
- Full verification: `pnpm verify` (preferred) or `make verify`
- Atlassian isolation: `pnpm verify:atlassian-isolation`
- Forge foundation: `pnpm verify:forge`
- Bootstrap Python must be 3.12 (`PYTHON=$(command -v python3.12) pnpm bootstrap`) when `python3` is 3.14+

## Definition of done

- Acceptance criteria are met.
- Tests, lint, typecheck, and build pass.
- Documentation reflects reality.
- `SCRATCHPAD.md` is updated.
- No unrelated changes remain.
