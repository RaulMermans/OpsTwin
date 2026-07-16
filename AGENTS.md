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

See `docs/sprints/SPRINT_04_SCENARIO_COMPARISON.md`, `docs/SCENARIO_COMPARISON_SPEC.md`, and `docs/METRIC_DEFINITIONS.md` for current scope and semantics.

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

## Definition of done

- Acceptance criteria are met.
- Tests, lint, typecheck, and build pass.
- Documentation reflects reality.
- `SCRATCHPAD.md` is updated.
- No unrelated changes remain.
