# Playback Performance

Local measurements only; no simulation rerun and no network request occur in this benchmark. Measured functions mirror `apps/web/lib/playback/normalize.ts` and `apps/web/lib/playback/timeline.ts` (see the script header).

| Items | Events | Normalization (ms) | Timeline construction (ms) | Checkpoints | Seek (ms) | Presentation bytes | Export bytes | Warnings |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 100 | 0.309 | 0.293 | 17 | 0.003 | 15117 | 16066 | 0 |
| 25 | 500 | 0.982 | 0.349 | 38 | 0.002 | 78451 | 80582 | 0 |
| 25 | 1000 | 0.654 | 0.593 | 54 | 0.001 | 157975 | 161002 | 0 |
| 50 | 2000 | 1.969 | 1.249 | 78 | 0.072 | 319736 | 324167 | 0 |
