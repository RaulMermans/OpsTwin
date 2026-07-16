# Product Slice Specification

## User and job

The user manages service operations and needs to compare bounded operating assumptions before changing a real workflow. They recognize ticket volume, staffing, processing time, escalation, rework, and SLA targets; they are not expected to understand JSON Schema, SimPy, common random numbers, or confidence-interval implementation.

## Journey and information architecture

`/` explains the product and support decision, shows the workflow, and opens `/workspace`. The workspace is a Scenario Lab: Baseline → Scenario set → Execution settings → Analysis. Analysis contains Overview, Metrics, Risk, Resources, and Technical evidence. Inputs remain visible after success or failure.

## Flow visualization

Flow follows execution settings and precedes result analysis. It offers Structure, Scenario changes, Operational pressure, and Baseline vs scenario. Structure and explicit changes work before execution; pressure and comparison require valid returned evidence. Result analysis retains Overview, Metrics, Risk, Resources, and Technical evidence.

The canonical source, stages, routes, completion, rework, resource pools, and assignments map into a frontend-only presentation model with stable IDs and positions. Relative intensity is labelled as display scaling, raw values remain visible, and unavailable evidence is not replaced with zero. Every visual relationship has a semantic list equivalent; the visualization cannot edit or persist the operational topology.

## Baseline

The canonical flow is Incoming tickets → Triage → Level 1 or Level 2 → Quality check → Resolved or rework. Editable fields are mean arrival interval, triage mean duration, Level 1 capacity, Level 2 capacity, quality-check duration, escalation probability, rework probability, and SLA target. Every field shows minutes, agents, or percent plus range guidance and an associated inline error.

## Guided scenarios

Up to three session-local scenarios are allowed. They have stable IDs and may be renamed, duplicated, deleted, and moved for display without changing backend ranking order:

- Demand change replaces Poisson `meanInterarrivalTime` after converting the chosen percentage.
- Staffing change replaces final Level 1 or Level 2 capacity.
- Process improvement replaces one supported processing parameter after converting the chosen reduction.
- Quality improvement replaces `quality-check` failure probability.

No raw IDs, paths, JSON, unsupported fields, or duplicate targets are exposed.

## Execution controls

Run count is 10, 25, 50, or 100; default 50. Objectives are SLA attainment, average cycle time, p95 cycle time, or queue length with registry-defined direction. Confidence defaults to 95%; base seed is visible in advanced evidence; optional guardrails use supported backend semantics. Estimated work is baseline items × runs × variants and submission stops above 30,000.

## Result hierarchy

1. Summary: selected objective, valid paired runs, first-ranked eligible scenario, guardrail result, mean change, and improvement probability.
2. Baseline health: SLA, average/p95 cycle, queue, terminal failure, and utilization.
3. Scenario impact: status, eligibility, rank, absolute/relative delta, improvement/degradation, risk, and guardrails.
4. Comparative ranking table using backend order and explanation.
5. Factual paired risk evidence.
6. Collapsed technical evidence: seeds, ratios, confidence method, hashes, representative seeds, integrity, work, and execution metadata.

The Scenario Lab adds a category-filtered responsive metric matrix, textual confidence intervals, improved/degraded/tied proportions, paired risk transitions, resource-pool evidence, factual primary statuses, one optional guardrail, sanitized local JSON/CSV exports, and a printable summary. Every value comes from the comparison response.

The phrase “Ranked first under the selected objective” is permitted. Recommendation, causal, significance, ROI, cost, and optimality language is prohibited.

## Errors and empty states

Designed states cover unavailable health, field/scenario validation, duplicate targets, no scenarios, UI/backend work guards, timeout, network failure, structured validation, failed scenarios, no eligibility, insufficient pairs, unexpected response, and empty result. Inputs and scenarios survive request failures; raw exceptions never render.

## Accessibility

Controls have programmatic labels and described errors. Loading is announced with a polite live region. Cancel and scenario controls work by keyboard. Tables have caption/header structure. Status always includes text, not colour alone. Focus is visible, motion is reduced when requested, and technical evidence is a native disclosure.

## Responsive behavior

Desktop uses an editorial two-column field sheet where useful; mobile becomes a single reading order without horizontal form scrolling. Data tables may use contained horizontal overflow while retaining headers. Primary actions remain reachable without fixed overlays.

## State and analytics

Local React state or a small reducer owns the session. No localStorage project persistence, accounts, analytics, database, or saved projects are included.

## Acceptance criteria

GM-069 through GM-080 add exact workflow mapping, deterministic layout, immutability, change targeting, evidence scaling, selection, comparison, semantic-text, responsive, and language gates. Blocked runtime gates remain explicit.

GM-042–GM-052, frontend unit/accessibility assertions, production build, local Services smoke, browser desktop/mobile flow, payload guard, and preview evidence when available must match `docs/VALIDATION_PLAN.md`.
