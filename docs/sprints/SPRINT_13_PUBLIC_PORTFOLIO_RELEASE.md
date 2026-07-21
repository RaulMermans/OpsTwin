# Sprint 13 — Public Release, Case Study README, and Portfolio Handoff

## Purpose

Sprint 13 adds no analytical capability. It makes the already-complete
product (Sprint 12.1, commit `26d76b3`) legible to hiring managers,
portfolio reviewers, and developers, and safe to expose publicly, while
keeping the repository private and unlicensed until the owner explicitly
approves those separate decisions.

## Scope

- Public-safety audit of all tracked files (secrets, local paths, temporary
  tokens, personal data).
- Stale-claim audit of current-state documentation.
- Repository governance: `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`,
  minimal issue/PR templates.
- License gate: no license added; explicit disclosure statement instead.
- Production screenshots and a Mermaid architecture diagram.
- Full case-study rewrite of `README.md`.
- `docs/PORTFOLIO_CONTENT_PACK.md` for external portfolio use.
- `docs/PUBLIC_CLAIM_REGISTER.md` mapping every public claim to evidence.
- `docs/PUBLIC_RELEASE_CHECKLIST.md` with GitHub metadata recommendations.
- `scripts/verify-public-release.mjs`, a deterministic, network-independent
  release-safety gate.
- Fresh full verification run (not inherited from Sprint 12.1), source
  package + clean-clone verification, and a production smoke/browser
  walkthrough.

## Non-goals

No change to simulation, ranking, sensitivity, economics, playback,
integrity, export, or request-contract behavior. No repository visibility
change. No license selection. No GitHub release or `v1.0.0` tag. No new
repository, Vercel project, or split of frontend/backend.

## Public-safety audit

`git ls-files`-scoped scans found no tracked `.env` file, no AWS/OpenAI/
GitHub-token/private-key patterns, no temporary Vercel share-link marker, and no
personal email address. Absolute local paths (`/Users/...`) appear only
inside historical sprint/ADR/superpowers-plan documents, which is
acceptable per the sprint's own audit rule (historical evidence, not
personal data); the one currently-live document referencing a Vercel `-git-`
hostname (`docs/VERCEL_PREVIEW_EVIDENCE.md`) is a production-deployment
alias, not a temporary share link. No build artifact, `node_modules`,
`.next`, `.vercel`, or virtual-environment path is tracked by Git.

## Stale-claim audit

`README.md` previously stated Vercel deployment was "one *proposed*"
project with "no Vercel project ... linked" and preview validation
"intentionally deferred" — contradicted by the live Sprint 11 production
deployment. Corrected as part of the README rewrite below.
`docs/ARCHITECTURE.md` previously stated "ADR-014 remains proposed until an
authenticated preview validates this configuration"; ADR-014 was accepted
2026-07-20 per the ADR file itself and the Sprint 11 production evidence —
corrected in place. `docs/ROADMAP.md` was silent past Sprint 12 (not
contradictory) — appended with dated Sprint 11/12.1/13 status lines, no
history rewritten. `docs/VALIDATION_PLAN.md` and
`docs/VERCEL_PREVIEW_EVIDENCE.md` already carry their own dated
reconciliation sections that supersede earlier "deferred/proposed" entries
in place — left as-is per the project's existing append-only convention.

## License gate

No `LICENSE` file exists in this repository. None was added this sprint.
`README.md` carries the required disclosure statement, and
`docs/PUBLIC_RELEASE_CHECKLIST.md` lists owner license selection as an open
item. Repository visibility and software licensing are documented as
separate decisions.

## Verification

Environment: macOS host, Node 22.22.3 via `nvm` (root default Node 20.20.0
cannot run `pnpm`/corepack — `ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING`,
matching prior sprints), Python 3.12.13 via the repository's `.venv`. The
`.venv`'s editable install of `opstwin-simulation-api` had gone stale since
Sprint 12.1 (`import app` failed with `ModuleNotFoundError` despite `pip
show` reporting it installed); reinstalling it
(`pip install --no-deps -e apps/simulation-api --force-reinstall`) resolved
it before any test ran — recorded here because it's exactly the kind of
environment drift this sprint's own instructions warn against silently
inheriting.

`pnpm verify` passed in full: `verify:node-portability`,
`verify:vercel-runtime` ("runtime baseline matches canonical example and
support.ts owns its runtime import"), Ruff ("All checks passed!"), ESLint
(0 issues, 51 source files), mypy strict (0 issues, 51 source files),
`tsc --noEmit`, backend pytest (**247 passed** in 7.90s), Vitest
(**172 passed**, 22 test files), the Next.js production build
("Compiled successfully"), the FastAPI distribution build, the canonical
CLI example, all benchmark smokes, `pnpm package:source` (336 files,
1,649,286 bytes, SHA-256 recorded in the manifest), `pnpm
verify:source-package`, and the new `pnpm verify:public-release` (all
checks passed, after one regex fix — see below). `git diff --check`
passed clean.

`scripts/verify-public-release.mjs` initially flagged one false positive:
a literal `C:\Users\...` (three elided dots) inside
`docs/VERCEL_PREVIEW_EVIDENCE.md`, documenting a historical Windows CLI
path-generation bug, matched the local-path regex because dots satisfied
the character class. Tightened the regex to require a real path character
after the username segment; re-ran clean.

**Clean-clone verification** (Phase 8, separate from the working tree):
extracted `artifacts/opstwin-source.zip` into an isolated scratch
directory and ran `pnpm bootstrap && pnpm lint && pnpm typecheck && pnpm
test && pnpm build` there from nothing but the archive. All passed,
including the identical 247/172 test counts — confirming no undocumented
local state is required beyond the documented prerequisites (the
temporary Python 3.12 default-vs-3.11 mismatch was resolved the same way
the main `.venv` requires: pointing `bootstrap` at Python 3.12 explicitly,
already documented as a prerequisite).

## Production smoke and browser walkthrough

`pnpm smoke:preview -- https://ops-twin.vercel.app` passed all eight
checks: `/` (200), `/workspace` (200), `/api/simulation/health` (200),
`/api/simulation/simulate` (200), `/api/simulation/simulate/repeated`
(200), `/api/simulation/compare/scenarios` (200 for the canonical 50-run
case; the two 422 rows are the smoke script's intentional
validation-error cases).

A live browser session against production ran the full journey: landing →
Guided setup (orientation dismissed) → 50-run paired comparison (Add one
Level 1 agent vs. Faster triage) → Summary → Flow (see the known defect
below) → Sensitivity (ran a live OFAT sweep on Level 1 agent capacity,
`observed mixed` monotonicity, 24 integrity checks) → Economics (assumptions
left blank, showing "Not configured" rather than a silent zero) → Playback
(clicked "Export playback JSON", zero console errors) → Technical (model
hash, integrity: passed · 16 checks) → Advanced workspace. Checked at
390×844, 768×1024, and 1440×900: `document.documentElement.scrollWidth`
equaled the viewport width at all three (no page-level horizontal
overflow), and zero console errors were logged at any point in the
walkthrough.

**Known defect found during this QA pass, not fixed (out of scope for a
documentation-only sprint):** the Flow tab's diagram/list container
(`.workflow-canvas` inside `.workflow-content`) renders at a reproducible
~10px width instead of filling its available space, in both the map and
list-equivalent views. Confirmed via DOM inspection in two independent
browser engines (headless Chromium via Playwright, and the interactive
Browser pane) at the same 1440×900 viewport; a manual `resize` event does
not correct it, so it's a static CSS sizing defect, not a stale-measurement
timing issue. No Flow screenshot was used in the README or portfolio pack
as a result (see `docs/SCREENSHOT_PLAN.md`), and a follow-up task was
flagged for a future session to fix it.

A minor, non-blocking observation: a handful of Next.js RSC-prefetch
requests (`?_rsc=...` query strings, fired by client-side link
hover/navigation) returned 404 during the walkthrough. Every real page
navigation and API call in the same session returned 200 (or the expected
422 for intentionally invalid input), and zero console errors resulted —
the browser's fallback to a full navigation on a failed prefetch is
invisible to a user. Noted for completeness, not treated as a release
blocker.

## Commits and deployment

Six focused commits (governance files; README case-study rewrite plus the
two stale-claim doc fixes; screenshot/architecture assets; portfolio
content and release checklist; the public-release verifier; this sprint's
evidence record and `SCRATCHPAD.md` update) were pushed to `origin/master`
per the owner's standing authorization for this sprint. The existing
`ops-twin` Vercel Services project (GitHub-integration auto-deploy, same
one domain, no new project) picked up the push. Exact commit SHAs and the
resulting deployed SHA are recorded in the session's final report rather
than duplicated here, to avoid restating the same fact twice in two
places that could drift out of sync.

## Public visibility gate

```text
Repository visibility change: pending owner approval
License decision: pending owner approval
GitHub Release/tag: pending owner approval
```

None of these three decisions were executed by this sprint.
