# OpsTwin

OpsTwin now opens the Scenario Lab in a Guided presentation: review the support-operation baseline, compare adding one Level 1 agent with faster triage, then inspect the observed result before deeper evidence. Advanced mode preserves the complete editor and technical workspace. Sensitivity, explicit-assumption economics, and deterministic representative playback remain available without changing their analytical contracts.

OpsTwin is a digital twin-style operational simulation and decision laboratory for testing service-workflow decisions. The local Scenario Lab organizes up to three guided interventions, explains the operational flow through a deterministic read-only map, and presents backend-owned paired comparison, uncertainty, risk, resource, guardrail, ranking, and integrity evidence without prescribing an action.

## Repository

- `apps/web`: Next.js landing page and accessible responsive Scenario Lab with a controlled workflow visualization.
- `apps/simulation-api`: stateless FastAPI health/simulation service, Pydantic models, seeded SimPy engine, CLI, and tests.
- `contracts`: JSON Schema Draft 2020-12 boundaries.
- `examples`: hand-calculated deterministic regression and bounded stochastic support model.
- `docs`: product, architecture, simulation, metrics, validation, roadmap, sprint, and ADR records.

## Supported development runtimes

The foundation was implemented and verified with Git 2.54.0, Node.js 24.14.0, pnpm 11.7.0, and Python 3.12.13. GNU Make is optional. No global installs are performed by the repository.

## Bootstrap

```sh
pnpm bootstrap
```

Bootstrap creates `.venv`, installs Python packages from `requirements.lock`, installs the local Python package without resolving new dependencies, and installs pnpm packages from `pnpm-lock.yaml`.

## Run

One command starts both services with the API origin configured automatically:

```sh
pnpm dev
```

It prints the Web, API, and Health URLs, fails clearly on a port conflict, and stops both processes on Ctrl+C or when either process exits. Separate-terminal development remains available:

```sh
pnpm dev:web
pnpm dev:api
```

The web app uses `http://localhost:3000`; the API uses `http://localhost:8000`. `pnpm smoke:local` starts both services and checks the public web/API routes through the same-origin Next.js rewrite with no manual `OPSTWIN_DEV_API_ORIGIN` step. Run the deterministic proof with:

```sh
cd apps/simulation-api
../../.venv/Scripts/python.exe -m app.cli ../../examples/support-deterministic.json
```

On POSIX, use `../../.venv/bin/python`. Run the seeded stochastic support example from the repository root with `pnpm run-example`. Single-run CLI/API output remains typed `0.3.0`; repeated execution uses `0.4.0`; `POST /compare/scenarios` and `python -m app.cli compare <request>` use `0.5.0`. Ordinary repeated and comparison runs are summary-only. Comparison retains at most the baseline and top-ranked-scenario representative evidence.

## Quality gates

```sh
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm verify
pnpm benchmark:simulation
pnpm benchmark:repeated
pnpm benchmark:comparison
pnpm benchmark:sensitivity
pnpm benchmark:economics
pnpm benchmark:economic-sensitivity
pnpm benchmark:playback
pnpm package:source
pnpm verify:source-package
```

`pnpm verify` is the preferred cross-platform gate. It runs both linters, both type checkers, tests, schemas, both builds, the example, the lightweight single/repeated/comparison/sensitivity/economics benchmark smokes, and clean deterministic source packaging plus its verification. Full workload matrices and `pnpm benchmark:playback` remain separate. Root scripts use pnpm's lifecycle Node executable and child tasks inherit that executable without manual `PATH` repair. Python is required when bootstrap must create `.venv`. `make verify` delegates to the same script when GNU Make is available.

`pnpm package:source` builds a deterministic, size-bounded `artifacts/opstwin-source.zip` with a SHA-256 manifest, excluding every generated/machine-specific path; `pnpm verify:source-package` re-opens the archive and checks it. Neither command is committed output — `artifacts/` is git-ignored.

## Local Scenario Lab

`/workspace` maps eight support-operation assumptions and up to three renameable, duplicable, deleteable, and locally ordered guided scenarios into the existing `0.5.0` paired comparison. Flow is available before execution in Structure and Scenario changes modes; Operational pressure and Baseline vs scenario modes require valid returned evidence. The presentation map is frontend-only, deterministic, read-only, keyboard-operable, and paired with a semantic list equivalent. Simulation mathematics, uncertainty, risks, guardrail evaluation, eligibility, and ranking remain in FastAPI. Result analysis is organized into Overview, Metrics, Risk, Resources, and Technical evidence. When a comparison result includes retained representative evidence, a Playback panel offers deterministic client-side reconstruction of one representative sampled run (see `docs/REPRESENTATIVE_PLAYBACK_SPEC.md`); it never represents aggregate certainty. JSON/CSV exports are sanitized and local; printing uses browser print styles.

Root `vercel.json` defines one proposed Vercel Services project with separate Next.js and FastAPI roots. See `docs/VERCEL_DEPLOYMENT.md`; no Vercel project is linked and preview validation remains intentionally deferred.

## Current scope

Operational model `0.2.0`, single-run `0.3.0`, repeated-run `0.4.0`, scenario-comparison `0.5.0`, and sensitivity `0.6.0` contracts remain stable. Economics uses separate `0.7.0` contracts. Presentation metadata never enters a request. Persistence, accounts, arbitrary topology editing, cloud sharing, and prescriptive guidance remain deferred.
