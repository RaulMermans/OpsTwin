# Usability Findings

## Before implementation — simulated/expert heuristic audit

No human participant testing was conducted during this implementation.

| Task | Finding | Severity | Outcome |
| --- | --- | --- | --- |
| Explain product | Landing copy described paired simulations before the operating decision. | High | Partial |
| Run comparison | Baseline fields, scenario editors, seed language, guardrails, and detailed settings appeared before the primary action. | Critical | Partial |
| Interpret result | Result evidence appeared after Flow, Sensitivity, Economics, and Playback. Ranking terminology was more prominent than a plain-language result. | Critical | Partial |
| Find workflow explanation | Flow was available but had no result-first cue. | Medium | Partial |
| Understand playback | Disclaimer was accurate but unreachable before completing the long page. | Medium | Partial |
| Find economics | Economics was discoverable only through page traversal, before the operational result. | Medium | Partial |

## Changes and simulated retest

Guided now opens with the decision question, concise baseline, two intervention cards, standard evidence strength, and one run action. Completed evidence renders immediately after the run panel, using response objective direction and paired probability/interval values. Evidence actions link users to Flow, Risk, Economics, Playback, and Technical evidence. Advanced preserves existing editors/settings. Orientation and glossary are keyboard-operable native controls.

The retest is automated/expert review only. Required participant metrics remain unmeasured until the protocol is run.

## Remaining issues

- Real participant task timing, ease scores, and comprehension must be collected before claiming target attainment.
- The session-local orientation intentionally returns on a full reload; it does not persist beyond the active session.
- Deep evidence panels remain feature-rich by design; their prerequisite messages and result-first navigation should be validated with participants.
- The production smoke check passed against the existing deployment, which predates these uncommitted Sprint 12 changes; deployment-specific Guided UI QA is therefore pending an authorized deployment.
