# Screenshot Plan

All screenshots are captured against the **production deployment only**,
`https://ops-twin.vercel.app` — never a temporary Vercel share or preview
URL. Assets live in `docs/assets/opstwin/`.

## Format deviation (disclosed)

The spec calls for `.webp`. This capture host has no local webp encoder
(`cwebp` is not installed; macOS `sips` on this host cannot encode webp:
`Can't write format: org.webmproject.webp`). Assets ship as optimized
`.png` instead. Dimensions, content, and captions otherwise match the spec
exactly; only the file extension differs. If a webp encoder becomes
available, re-encoding these PNGs losslessly is a mechanical follow-up, not
a recapture.

## Capture method

Captured with a throwaway Playwright/Chromium script (not committed —
`playwright-core` was installed only in a scratch directory outside the
repository, and no `package.json` dependency was added). The script drove
the real Guided flow: skip orientation, run the default guided comparison
(Add one Level 1 agent vs. Faster triage, 50 paired runs), then visited
each evidence tab. Viewport: 1440×900 for all still images.

## Canonical states

| # | Filename | Captured | Notes |
| - | --- | --- | --- |
| 01 | `01-landing.png` | Yes | Landing page hero and "what you will do" panel |
| 02 | `02-guided-setup.png` | Yes | Guided baseline + two-scenario setup, orientation dismissed |
| 03 | `03-guided-result.png` | Yes | Summary tab after a completed comparison |
| 04 | `04-flow-evidence.png` | **Not produced** | See "Known defect" below |
| 05 | `05-risk-evidence.png` | Yes | Risk tab |
| 06 | `06-resource-evidence.png` | Yes | Resources tab |
| 07 | `07-sensitivity.png` | Yes | Sensitivity tab, after running the default OFAT sweep |
| 08 | `08-economics.png` | Yes | Economics tab with assumptions left blank (see caption) |
| 09 | `09-playback.png` | Yes | Playback tab, baseline representative run |
| 10 | `10-advanced-workspace.png` | Yes | `/workspace?mode=advanced` |
| 11 | `11-guided-before-after.png` | **Not produced** | No genuine pre-Sprint-12 screenshot exists to pair with an "after" — fabricating one is explicitly against this sprint's rules |
| — | `social-preview.png` | Yes | 1280×640 designed card, not a live-app screenshot |

Nine of the ten numbered product screenshots were produced; the README
uses eight of them as its purposeful visuals (within the 6–10 range), plus
the Mermaid architecture diagram embedded directly in the README text.

## Known defect discovered during capture (04-flow-evidence)

While capturing the Flow tab, the diagram/list container (`.workflow-canvas`
inside `.workflow-content`) reproducibly renders at ~10px wide instead of
filling its available space, in both the map (SVG) and list-equivalent
views. Confirmed via DOM inspection in two independent browser sessions
(headless Chromium and the in-app Browser pane) at the same 1440×900
viewport; a manual resize event does not correct it, so it is a static CSS
sizing defect, not a stale-measurement timing issue. This is a genuine,
currently-live production defect — not a screenshot artifact — and it is
out of scope for this documentation-only sprint to fix. A screenshot that
made this look like working evidence would violate the "show valid
production behavior" requirement below, so no Flow screenshot is shipped.
The defect is tracked as a follow-up (see `SCRATCHPAD.md` Sprint 13 entry)
and is not hidden from this plan.

## Requirements checklist (per asset)

- [x] Canonical demo inputs only (default baseline, default two scenarios, 50 runs)
- [x] Valid production behavior (excluding the known Flow defect above)
- [x] No personal browser data, no console/debug UI
- [x] No temporary access token, no local filesystem path
- [x] Consistent 1440×900 desktop viewport for all still images
- [x] Legible text at README display width
- [x] Optimized file size (44 KB–172 KB per asset; social preview 104 KB)
- [x] Descriptive filenames
- [x] Alt text and README placement documented below

## Secondary viewport verification (not separate image assets)

Verified via the same script (no separate screenshot files, per spec's "do
not place ten full-width screenshots consecutively" guidance — this is
layout verification, not a visual asset):

| Viewport | `document.documentElement.scrollWidth` | Horizontal overflow |
| --- | --- | --- |
| 390×844 | 390 | No |
| 768×1024 | 768 | No |

## README placement and alt text

| Filename | README section | Alt text |
| --- | --- | --- |
| `01-landing.png` | Hero | "OpsTwin landing page: 'Test an operating change before the queue feels it,' with links to try the guided comparison or open the advanced workspace." |
| `02-guided-setup.png` | The solution | "Guided setup screen showing the immutable baseline and two candidate scenarios, Add one Level 1 agent and Faster triage, ready to compare." |
| `03-guided-result.png` | Product walkthrough | "Guided result summary after a 50-run paired comparison, showing observed cycle-time change, improvement probability, and uncertainty range for both scenarios." |
| `05-risk-evidence.png` | Key capabilities — Workflow and resource evidence | "Risk evidence tab for the completed comparison." |
| `06-resource-evidence.png` | Key capabilities — Workflow and resource evidence | "Resource evidence tab showing operational pressure on staffing pools." |
| `07-sensitivity.png` | Key capabilities — Sensitivity | "Sensitivity tab after running a one-factor-at-a-time sweep on Level 1 agent capacity, showing the observed response curve and integrity check count." |
| `08-economics.png` | Key capabilities — Economics | "Economics tab with cost assumption fields left blank, illustrating that blank fields remain unconfigured rather than defaulting to zero." |
| `09-playback.png` | Key capabilities — Representative playback | "Representative playback tab showing the baseline representative run's timeline controls and run-level event summary." |
| `10-advanced-workspace.png` | Architecture / Advanced mode | "Advanced workspace at /workspace?mode=advanced, showing the full editable baseline and scenario controls." |
| `social-preview.png` | GitHub repository social preview (manual upload) | "OpsTwin: Test an operating change before the queue feels it — paired simulation evidence for service-operation decisions, comparative not prescriptive, with a screenshot of a completed guided comparison result." |

## Manual step required (owner action)

`social-preview.png` must be uploaded manually to the repository's GitHub
**Settings → General → Social preview** — this is a GitHub settings change
and is not performed by this sprint's automation. See
`docs/PUBLIC_RELEASE_CHECKLIST.md`.
