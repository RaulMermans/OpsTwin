## Summary

<!-- One or two sentences: what changed and why. -->

## Scope check

- [ ] This change is bounded to one concern (not a bundle of unrelated fixes)
- [ ] No existing contract (`0.2.0`–`0.7.0`) changed shape/semantics without an ADR
- [ ] No new dependency was added without justification in the PR description
- [ ] No secrets, tokens, or `.env` files are included

## Verification

<!-- Paste the commands you ran, not full log output. -->

- [ ] `pnpm lint`
- [ ] `pnpm typecheck`
- [ ] `pnpm test`
- [ ] `pnpm test:web`
- [ ] `pnpm build`
- [ ] `pnpm verify` (full gate, expected before merge)

## Documentation

- [ ] Relevant spec / `docs/METRIC_DEFINITIONS.md` updated if behavior changed
- [ ] `SCRATCHPAD.md` updated for non-trivial changes
