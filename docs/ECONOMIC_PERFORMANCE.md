# Economic Performance Baseline

## Measurement protocol

Benchmarks are serial and local. Simulation execution time and economic-evaluation time are recorded separately. Matrices report items, runs, variants or values, unchanged work units, total time, canonical response bytes, paired ratio, retained ordinary events, and integrity status.

## Economic comparison

Executed locally on Windows 11 with Python 3.12.13, serially, on 2026-07-16.

| Items | Runs | Scenarios | Variants | Work units | Simulation s | Economic s | Total s | Response bytes | Paired ratio | Snapshots | Undefined / completion | Retained events | Integrity |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 100 | 10 | 1 | 2 | 2,000 | 0.7342 | 0.0056 | 0.7398 | 43,286 | 1.0 | 20 | 0 | 0 | passed / 24 |
| 100 | 50 | 2 | 3 | 15,000 | 4.9979 | 0.0368 | 5.0347 | 77,449 | 1.0 | 150 | 0 | 0 | passed / 24 |
| 100 | 100 | 2 | 3 | 30,000 | 9.5920 | 0.0756 | 9.6676 | 81,780 | 1.0 | 300 | 0 | 0 | passed / 24 |
| 1,000 | 10 | 2 | 3 | 30,000 | 10.9996 | 0.0072 | 11.0068 | 73,127 | 1.0 | 30 | 0 | 0 | passed / 24 |

## Economic sensitivity

Executed in the same environment. Economics reused the 0.6.0 sweep and added no simulation work units.

| Items | Runs | Values | Work units | Simulation s | Economic s | Total s | Response bytes | Paired ratio | Snapshots | Undefined / completion | Retained events | Integrity |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 100 | 10 | 3 | 3,000 | 1.1616 | 0.0070 | 1.1686 | 18,851 | 1.0 | 30 | 0 | 0 | passed / 23 |
| 100 | 50 | 5 | 25,000 | 10.3022 | 0.0756 | 10.3778 | 32,654 | 1.0 | 250 | 0 | 0 | passed / 23 |
| 100 | 100 | 5 | 50,000 | 23.3071 | 0.1503 | 23.4574 | 34,955 | 1.0 | 500 | 0 | 0 | passed / 23 |

The measurements characterize this local run only and are not hosting guarantees.

## Environment note

Repository-wide build and test gates can be blocked on this Windows sandbox by inaccessible pip/build/pytest temporary roots and child-process restrictions. Such blocks are reported independently from executed benchmark results and are never converted into passes.
