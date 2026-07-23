# Sprint 15.1 — Process and acceptance closure

## Scope

This is a presentation-only local hotfix over the existing operational,
comparison, sensitivity, economic, and playback contracts. It does not change
simulation formulas, API contracts, seeds, ranking, or returned evidence.

## Production reproduction and root cause

On 2026-07-23, a rendered production comparison was opened at
`https://ops-twin.vercel.app/workspace` and Process was measured through the
browser DOM. The Process section was 1168 px wide while its canvas was only
321 px wide; the internal grid retained its 640 px minimum and was clipped.
The first collapsing element was `.workflow-content`, but its cause was its
parent: `.workflow-section` inherited the landing page's two-column grid.
The browser computed section tracks of `321.047px 650.555px`, auto-placing
`.workflow-content` in the first, narrow track.

The local repair explicitly makes `.workflow-section` a block layout. Change
summary content now spans the map grid above the canvas, while an open
inspector occupies the adjacent track only at wide desktop sizes and stacks
below the map at smaller widths.

## Local presentation changes

- Guided Process map nodes use business labels and hide node kinds and
  distribution labels. Guided change summaries use prose; the detailed
  changes table remains Advanced-only.
- Resource cards show percentage-point and wait differences plus peak use as
  `used of configured capacity`. The workload conclusion compares returned
  baseline and valid proposed-change resource evidence.
- Guided sensitivity hides ordinary workload metadata and contains technical
  evidence in one collapsed disclosure.
- Per-agent-minute cost inputs show a selected-currency per-agent-hour
  equivalent when the entered rate is finite.
- Playback keeps run index, seed, selection method, model hash, raw IDs, and
  exact ledger entries in `Show technical run details`; the primary state
  tables use business labels and aggregate full-capacity notices per team.

## Verification status

- Passed: direct web ESLint (`eslint . --max-warnings=0`), direct web
  TypeScript (`tsc --noEmit`), and `git diff --check`, using the bundled Node
  runtime.
- Blocked: focused Vitest did not execute tests. Its JSDOM worker failed to
  start because reading JSDOM timed out with `ETIMEDOUT`; the failure occurred
  before test collection.
- Not yet run: rendered local regression at all target viewports, full
  verification, production deployment, production smoke, runtime-error
  checks, screenshot refresh, and manual desktop QA.

Manual mobile QA was not performed. No commit, push, deployment, screenshot,
or participant-study claim is made by this local record.

## Reference

The repository continues to list
[Awesome Vibe Coding](https://github.com/filipecalegario/awesome-vibe-coding.git)
as a research reference in `docs/REFERENCES.md`.
