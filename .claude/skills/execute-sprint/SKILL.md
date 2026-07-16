---
name: execute-sprint
description: Manually execute one supplied OpsTwin sprint document from planning through verification; do not use for ad hoc tasks or multi-sprint work.
disable-model-invocation: true
argument-hint: "<sprint-document-path>"
---

# Execute sprint

1. Require a sprint-document path argument.
2. Read `CLAUDE.md`, then the specified sprint, then only linked specifications relevant to the current task.
3. Inspect `git diff` before editing and create a bounded plan.
4. Implement only sprint scope with executable verification.
5. Run the sprint's quality gates and update `SCRATCHPAD.md` after meaningful milestones.
6. Report changed files, commands run, failures, and unresolved risks.

Never commit or push.
