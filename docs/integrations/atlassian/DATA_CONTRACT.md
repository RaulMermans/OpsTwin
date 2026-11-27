# Data contract

CG-1 remote request `cg1.v1` selects a synthetic catalog experiment and intervention parameters. It is not an operational-model payload and must not include `baselineModel`, issues, or tokens.

CG-2 operational snapshots use `contracts/operational-snapshot.schema.json` (`os.1.0.0`). They are not Core models and are not sent to `/api/integrations/atlassian/v1/compare`.

Integration data is **not** a Core schema change. The simulation adapter still emits operational model `0.2.0` and comparison request `0.5.0`.

## Mapping intent

| JSM observation | Core field | Status |
|---|---|---|
| Project key / name | provenance only, not simulated | observe |
| Request type counts | source mix / arrival process | derive or assume |
| Created timestamps | arrival process | derive |
| Status changelog | stage occupancy proxy | derive with bias |
| Assignee / team size | `resourcePools[].capacity` | derive or assume |
| SLA goals / cycles | `slaRules.targetDuration` | observe / calendar mismatch |
| Worklogs | handling time | observe if present, else unknown |
| Resolution + reopen | rework / failure probability | derive |
| Issue summary/description | **do not persist or forward** | privacy |

## Forbidden

- Inferring Core metrics inside Forge without running the engine
- LLM-generated numeric model parameters
- Silent topology edits (new stages/routes) — rejected by existing materializer
