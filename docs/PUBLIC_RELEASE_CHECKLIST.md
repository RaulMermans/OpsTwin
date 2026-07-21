# Public Release Checklist

This checklist tracks what's ready for public visibility and what remains
an explicit owner decision. Completing this checklist does **not** change
repository visibility, select a license, or create a release tag — those
three actions require separate, explicit owner approval (see the gate at
the bottom).

## Public-safety audit findings

Scan method: `git ls-files`-scoped `git grep` across all tracked files
(never a filesystem-wide scan) for secret patterns, temporary Vercel share-link markers,
absolute local paths, and personal email addresses; a tracked-file check
for `.env`, build artifacts, and virtual environments.

| Finding | Classification | Notes |
| --- | --- | --- |
| No tracked `.env` file | Safe to retain | Confirmed via `git ls-files` |
| No AWS/GitHub-token/private-key/OpenAI-style secret pattern in any tracked file | Safe to retain | `git grep` across all tracked files, zero matches |
| No temporary Vercel share-link marker anywhere | Safe to retain | Zero matches |
| No personal email address in any tracked file | Safe to retain | Zero matches for the owner's email |
| No `node_modules`/`.next`/`.vercel`/`__pycache__`/`.venv`/build artifact tracked | Safe to retain | Confirmed via `.gitignore` and `git ls-files` |
| Absolute `/Users/...` paths inside historical sprint/ADR/superpowers-plan documents | Safe to retain | Historical evidence of a real development environment, not personal data — per this sprint's own audit rule |
| `docs/VERCEL_PREVIEW_EVIDENCE.md` references a `-git-master-` Vercel alias hostname | Safe to retain | This is a production-deployment alias, not a temporary share link — no share-link marker exists anywhere in the repository |
| README stated Vercel deployment as "proposed" with "no Vercel project linked" | **Fixed this sprint** | Was stale against the live Sprint 11 production deployment; corrected in the README rewrite |
| `docs/ARCHITECTURE.md` stated "ADR-014 remains proposed" | **Fixed this sprint** | ADR-014 was accepted 2026-07-20; corrected in place |
| No license file | Requires owner decision | See License gate below |
| Repository visibility | Requires owner decision | See Visibility gate below |

## Code

- [x] Backend tests (`pnpm test`) — re-run fresh this sprint, count recorded in `docs/sprints/SPRINT_13_PUBLIC_PORTFOLIO_RELEASE.md`
- [x] Frontend tests (`pnpm test:web`) — re-run fresh this sprint
- [x] Lint (`pnpm lint`)
- [x] Types (`pnpm typecheck`)
- [x] Builds (`pnpm build`)
- [x] Contracts unchanged (`0.2.0`–`0.7.0`, verified by source inspection — no contract file touched this sprint)
- [x] Source package (`pnpm package:source` + `pnpm verify:source-package`)
- [x] Secret scan (see audit table above)
- [x] Local-path scan (see audit table above)

## Product

- [x] Landing — verified in production browser walkthrough
- [x] Guided — verified (default comparison run against production)
- [x] Advanced — verified (`/workspace?mode=advanced`)
- [x] Comparison — verified (50-run paired comparison completed live)
- [x] Evidence panels (Flow, Risk, Resources, Sensitivity, Economics, Playback, Technical) — verified, **with one known exception**: the Flow diagram/list container has a reproducible width-collapse defect discovered during this sprint's screenshot capture (see `docs/SCREENSHOT_PLAN.md`); tracked as a follow-up, not fixed in this documentation-only sprint
- [x] Exports (JSON export from Playback verified with zero console errors; CSV/JSON export behavior otherwise covered by the 172-test frontend suite)
- [x] Responsive QA (390×844, 768×1024, 1440×900) — verified, zero horizontal overflow and zero console errors at all three viewports post-comparison

## Documentation

- [x] README rewritten as a case study
- [x] Architecture documented (Mermaid diagram in README + `docs/ARCHITECTURE.md`)
- [x] `SECURITY.md`
- [x] `CONTRIBUTING.md`
- [x] `CHANGELOG.md`
- [x] Limitations stated explicitly (README + this checklist + claim register)
- [x] License state disclosed explicitly (no license, disclosure sentence in README)
- [x] `docs/PUBLIC_CLAIM_REGISTER.md`

## Assets

- [x] Screenshots captured from production only (`docs/SCREENSHOT_PLAN.md`)
- [x] Architecture visual (Mermaid, embedded in README — no separate PNG needed)
- [x] Social preview (`docs/assets/opstwin/social-preview.png`, 1280×640, 104 KB)
- [x] Alt text for every embedded/manifested image
- [x] Image optimization (44 KB–172 KB per product screenshot, 104 KB social preview)
- [x] Format deviation disclosed: `.png` instead of `.webp` (no local webp encoder available — see `docs/SCREENSHOT_PLAN.md`)

## Community files — decision recorded

Created: `.github/ISSUE_TEMPLATE/bug_report.yml`,
`.github/pull_request_template.md`. **Not created:** `CODE_OF_CONDUCT.md`,
`.github/ISSUE_TEMPLATE/feature_request.yml`. Rationale: this is a
solo-maintained portfolio repository, not yet actively seeking broad
contribution; a bug-report template and PR template are sufficient per
this sprint's own instruction not to build contribution-heavy
infrastructure "merely for appearance." Revisit if the repository becomes
public and starts receiving external contributions.

## License gate

No `LICENSE` file exists (confirmed by audit). None was added this sprint.
**Owner action required:** select a license before encouraging reuse, or
explicitly decide to keep the project source-visible-only. Repository
visibility and software licensing are separate decisions — making the
repository public does **not** imply permission to copy, modify, or
redistribute it.

## GitHub metadata recommendations (recommendations only — nothing applied)

Current state, read via `gh repo view`/`gh api` (read-only, no changes
made):

| Setting | Current value | Recommendation |
| --- | --- | --- |
| Description | *(empty)* | `Operational simulation and decision lab for comparing service-workflow interventions with paired stochastic evidence, sensitivity, economics and representative playback.` |
| Website | `https://ops-twin.vercel.app` | Already correct — no change needed |
| Topics | *(none set)* | `discrete-event-simulation`, `operations-research`, `decision-support`, `service-operations`, `stochastic-simulation`, `simpy`, `fastapi`, `nextjs`, `typescript`, `python`, `sensitivity-analysis`, `queueing`, `digital-twin`, `vercel` (14 topics, under GitHub's limit) |
| Social preview | Not set | Manually upload `docs/assets/opstwin/social-preview.png` via Settings → General → Social preview |
| Issues | Enabled | Keep enabled |
| Discussions | Disabled | Recommendation-only: leave disabled unless the owner wants public Q&A; not required for release readiness |
| Private vulnerability reporting | Not confirmed enabled (requires public repo or GitHub Advanced Security to verify via API) | Enable once repository visibility is decided; `SECURITY.md` already prefers this channel |
| Dependabot | Not confirmed (API reports `security_and_analysis: null` for this private repo) | Recommend enabling Dependabot alerts once visibility/plan allows |
| Secret scanning | Not confirmed (same API limitation) | Recommend enabling once available under the repository's plan/visibility |
| Push protection | Not confirmed (same API limitation) | Recommend enabling alongside secret scanning |
| Branch protection on `master` | Not queryable on this plan while private (`403: Upgrade to GitHub Pro or make this repository public`) | Recommend a required-status-checks rule (CI passing) before merge, once feasible to configure |
| Repository visibility | **Private** | Owner decision — not changed by this sprint |
| License | **None** | Owner decision — not changed by this sprint |

No `gh repo edit`, `gh api` write call, or GitHub settings change was
executed by this sprint. Every row above was read, not written.

## Public visibility gate

```text
Repository visibility change: pending owner approval
License decision: pending owner approval
GitHub Release/tag: pending owner approval
```

None of these three actions were performed by this sprint, regardless of
how complete the rest of this checklist is.
