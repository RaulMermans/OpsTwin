# Contributing to OpsTwin

OpsTwin is a solo-maintained portfolio project. It is not currently seeking
broad open-source contribution, but the process below applies to any change
a maintainer or collaborator makes, and to any external contribution that is
accepted.

## Project scope

OpsTwin simulates a **canonical support-operations workflow** (customer
support, claims, onboarding, and back-office requests) — it is not a
general-purpose workflow builder, and contributions that generalize the
model beyond this wedge are out of scope unless they come with a matching
ADR (see `docs/ARCHITECTURE.md`, `docs/PROJECT_BRIEF.md`).

## Required reading, in order

Read before proposing or reviewing any change:

1. [`CLAUDE.md`](CLAUDE.md) — non-negotiables and priorities.
2. [`README.md`](README.md) — product overview and how to run it.
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system boundaries.
4. [`docs/VALIDATION_PLAN.md`](docs/VALIDATION_PLAN.md) — how correctness is
   verified.
5. The specification relevant to the area you're touching (e.g.
   `docs/SCENARIO_COMPARISON_SPEC.md`, `docs/SENSITIVITY_ANALYSIS_SPEC.md`,
   `docs/ECONOMIC_COMPARISON_SPEC.md`, `docs/REPRESENTATIVE_PLAYBACK_SPEC.md`).
6. The relevant ADR in [`docs/adrs/`](docs/adrs/), if one exists for the
   decision you're revisiting.

This project also draws on
[Awesome Vibe Coding](https://github.com/filipecalegario/awesome-vibe-coding.git)
as a reference for agentic/AI-assisted development practices — useful
background if you're contributing with AI assistance yourself.

## Local setup

```sh
pnpm bootstrap
pnpm dev
pnpm verify
```

See the README's "Run locally" section for prerequisites and expected URLs.

## Branch and change policy

- Work in a feature branch; open a pull request against `master`.
- Keep changes **focused and bounded to one concern** — a bug fix should not
  bundle a refactor, and a documentation change should not bundle behavior
  changes.
- Do not force-push a shared branch and do not rewrite published history.

## Required tests

Every behavior change needs an executable verification path. At minimum,
before opening a pull request:

```sh
pnpm lint
pnpm typecheck
pnpm test
pnpm test:web
pnpm build
```

`pnpm verify` is the full preferred gate and is expected to pass before
merge.

## Contract compatibility

OpsTwin's request/response contracts are explicitly versioned (operational
model `0.2.0`, single simulation `0.3.0`, repeated simulation `0.4.0`,
scenario comparison `0.5.0`, sensitivity `0.6.0`, economics `0.7.0`). Do not
change an existing contract's shape or semantics without a version bump and
an accompanying ADR explaining the change. Silently changing a metric
definition or simulation semantic without updating
`docs/METRIC_DEFINITIONS.md` is not acceptable.

## Deterministic fixtures

Tests that exercise randomness must use fixed, documented seeds. A test
that can produce different pass/fail outcomes across runs without a seed
change is a defect, not an acceptable flake.

## Language and claims

Avoid prescriptive or causal language in product copy and code comments
(e.g. "recommended," "optimal," "guaranteed," "best decision," "root
cause"). This project reports comparative simulation evidence, not
recommendations — see `docs/SCENARIO_COMPARISON_SPEC.md` for the exact
boundary language expected throughout the UI.

## Security

Do not commit secrets, API keys, tokens, or `.env` files. See
[`SECURITY.md`](SECURITY.md) for how to report a vulnerability instead of
opening a public issue for one.

## Documentation requirements

Update the relevant spec, ADR, or `docs/METRIC_DEFINITIONS.md` whenever
behavior changes. Keep `SCRATCHPAD.md` current for any non-trivial change
performed by an AI-assisted session.

## Out of scope

The following are explicitly not accepted without a prior ADR and explicit
maintainer sign-off: an arbitrary workflow/topology builder, a database or
persistence layer, user accounts or authentication, cloud sharing, causal
or prescriptive recommendation logic, and splitting the frontend and
backend into separate deployments or repositories.
