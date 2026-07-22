# Plain-language standard

## Purpose

Guided mode helps an operations manager understand a bounded simulation
comparison without needing simulation or statistical vocabulary. It reports
returned evidence; it does not make a recommendation or prediction.

## Language layers

1. **Primary Guided wording** uses the business term needed to complete the
   task: *Current operation*, *Proposed change*, *Result to measure*,
   *matched simulated operating days*, and *plausible range*.
2. **Secondary technical wording** may appear in concise help or parentheses
   when it helps someone connect a business term to a technical term.
3. **Technical wording** remains unchanged in Advanced mode, Technical
   details, API contracts, schemas, exports, and engineering documentation.

## Central terms

| Technical term | Primary Guided wording |
| --- | --- |
| Baseline | Current operation |
| Scenario | Proposed change |
| Objective | Result to measure |
| Average cycle time | Average time to resolve a ticket |
| P95 cycle time | Time within which 95% of tickets were resolved |
| SLA attainment | Tickets resolved within the target time |
| Time-weighted queue length | Average number of tickets waiting over time |
| Paired simulations / paired runs | Matched simulated operating days / matched tests |
| Evidence strength | Number of matched tests |
| Guardrail | Required condition |
| Ranking | Observed order |
| Improvement probability | How often the change performed better |
| Confidence interval | Plausible range of the average result |
| Sensitivity | Test assumptions |
| Operational pressure | Where queues and workload build up |
| Resource evidence | Team workload |
| Representative playback | One example simulated run |
| Economics | Costs |
| Eligibility | Whether required conditions were met |

Seed schedules, deterministic seeds, contract versions, and work units are
technical details, not primary Guided labels.

## Result rules

Guided results always distinguish a higher observed average from conclusive
evidence. They use the backend ranking, returned direction, mean delta,
improvement probability, successful paired counts, eligibility, and returned
interval only. A range crossing no change is described as inconclusive; no
copy calls it proven, guaranteed, optimal, or recommended. Proportion deltas
are shown in percentage points, never as a percent change.
