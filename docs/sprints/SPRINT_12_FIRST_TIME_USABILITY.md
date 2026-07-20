# Sprint 12 — First-Time Usability and Guided Decision Flow

## Objective

Make the existing paired scenario comparison understandable and runnable by a first-time operations user without changing analytical capabilities, requests, results, exports, or simulation semantics.

## Scope

- Guided is the session-default presentation mode; Advanced exposes the existing workspace controls.
- The default comparison remains Add one Level 1 agent versus Faster triage, using the unchanged 50-run average-cycle-time request.
- A concise baseline summary, intervention cards, run expectation, result-first summary, evidence navigation, orientation, glossary, and landing demonstration path are presentation-only.

## Non-goals

No new endpoint, contract, simulation calculation, ranking, objective direction, integrity check, export shape, analytics, persistence, or dependency is introduced.

## Acceptance evidence

Automated web tests cover Guided default state, a valid no-edit request, result-first ordering, objective-direction-aware summary, probability/uncertainty disclosure, non-prescriptive wording, evidence navigation, orientation dismissal, glossary access, and Advanced control preservation. Human testing is tracked separately in `docs/USABILITY_TEST_PLAN.md` and has not been represented as completed by implementation evidence.
