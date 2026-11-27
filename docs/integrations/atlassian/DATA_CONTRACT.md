# Data contract

CG-1 remote request `cg1.v1` selects a synthetic catalog experiment and intervention parameters. It is not an operational-model payload and must not include `baselineModel`, issues, or tokens.

CG-2 operational snapshots use `contracts/operational-snapshot.schema.json` (`os.1.0.0`). They are not Core models and are not sent to `/api/integrations/atlassian/v1/compare`. Runtime ingest validates required canonical fields before returning success.

CG-3 calibration artifacts use `cal.1.0.0` (`apps/simulation-api/app/calibration/contracts.py`). `POST /api/integrations/atlassian/v1/calibrate` accepts synthetic fixture identifiers only. Live snapshots are not a remote calibration input.

CG-4 transformation experiments use `cg4.v1`. `POST /api/integrations/atlassian/v1/transform` accepts a synthetic fixture identifier, a catalog intervention, and experiment execution (`itemCount` 20–80). It does not accept `baselineModel`, snapshots, or issues. Canonical calibrated `itemCount=1` is not an executable demand volume.

CG-5 multi-scenario experiments use `cg5.v1` on the same path: fixture identifier plus up to three named alternatives. `cg5-hybrid-support` is the synthetic template with an existing triage completion route. Hybrid auto-complete is refused when that route is absent.

JQL cohort filters use `yyyy-MM-dd HH:mm` in the caller's timezone (UTC padded ±1 day when timezone is unknown). Exact UTC window bounds are applied during normalization. Current `resolutiondate` does not reconstruct every historical open interval. Status residence is not processing time. Mixed synthetic/observed records keep per-case origin; live transport is not origin.

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
