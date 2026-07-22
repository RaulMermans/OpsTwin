# Sprint 14 manual QA

## Persona

Business operations manager who understands staffing, queues, and service
targets but not simulation or statistical terminology.

## Owner walkthrough checklist

Run the default Guided comparison, then check that the user can identify:

1. OpsTwin compares proposed operating changes before implementation.
2. The current support operation and the two proposed changes.
3. The result to measure and what its business label means.
4. The higher observed average and whether the plausible range is
   inconclusive, favorable, unavailable, or unfavorable.
5. The meaning of matched tests, the plausible range, Process, Team
   workload, Example run, Costs, and Technical details.
6. That OpsTwin does not predict exactly what will happen.

Record, for each task: correct/incorrect, unknown terms, hesitation,
incorrect clicks, elapsed time, assistance, and ease (1–7). Do not use
repository knowledge to answer the tasks.

## Required journey and viewports

Landing → Guided setup → Run comparison → Result → Process → Uncertainty →
Team workload → Test assumptions → Costs → Example run → Technical details
→ Advanced → JSON export → CSV export.

Check 390×844, 768×1024, 1440×900, and (for Flow) 1728×1117 for contained
overflow, keyboard tabs/focus, console and hydration errors, stale result
reset, export integrity, visible list alternative, and Flow inspector
behavior.

## Status

Not executed in this local implementation session. No participant study or
owner walkthrough is claimed.

## 2026-07-22 closure attempt

Not executed. The local frontend runner cannot start because Vite fails during
dependency initialization (`picomatch` parser mismatch), so the required
rendered-browser journey and owner walkthrough remain pending. This is not
participant evidence and does not change the status above.
