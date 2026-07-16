---
paths:
  - "contracts/**/*.json"
  - "examples/**/*.json"
---

# Contract rules

- Keep contracts implementation-neutral and units explicit.
- Reject negative capacities, durations, and rates.
- Include schema versioning and disallow unexpected properties where practical.
- Add only fields required by accepted use cases.
- Validate examples against their schema.
