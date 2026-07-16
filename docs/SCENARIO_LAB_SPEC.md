# Scenario Lab Specification

## Purpose

Help an operations user compare bounded interventions with a baseline, understand uncertainty and operational trade-offs, and inspect the evidence behind backend comparative ranking.

## User

An operations or business user who recognizes demand, staffing, processing, quality, service levels, queues, and resource load but is not expected to understand JSON contracts or statistical implementation.

## Job to be done

When considering operational changes, organize a small scenario set and see how each differs from baseline, how certain those paired differences are, and which service, flow, risk, and resource trade-offs appear.

## Baseline

The canonical support model remains immutable during the session. Its editable display assumptions map to a new model copy for submission and remain visible after requests. Baseline evidence is the backend aggregate and representative result, never frontend-derived statistics.

## Scenario collection

One to three UI scenarios use stable session IDs and approved guided overrides. Users can rename, duplicate, delete, and move scenarios with buttons. Names must be non-empty. Duplication copies configuration under a new unique ID and name but no evidence. Edits invalidate stale results. Display order never changes backend ranking order.

## Scenario statuses

Every returned scenario maps to one primary textual state: Ranked; Eligible but unranked; Ineligible - guardrail failed; Invalid scenario; Execution failed; Insufficient valid runs; Insufficient paired runs; Completed without ranking; or Result unavailable. Unknown shapes map safely to Result unavailable. Rank is shown only when returned; absent metrics are unavailable.

## Objectives

The user selects one backend-supported objective and its registry-defined direction: SLA attainment is higher-is-better; average cycle, p95 cycle, and queue length are lower-is-better. Resource utilization is never introduced as an objective.

## Guardrails

At most one optional guardrail is submitted. Supported metrics determine the legal operator and unit: minimum SLA uses greater-than-or-equal; maximum cycle, p95, queue, and supported resource utilization use less-than-or-equal. Disabled guardrails are omitted. Invalid thresholds block submission. The backend owns pass/fail. Copy distinguishes no guardrail, passed, and failed.

## Comparison overview

Show objective, valid paired count, scenario count, eligible and failed/ineligible counts, first-ranked eligible scenario when present, objective mean delta, probability of improvement, guardrail state, and the most relevant returned risk change. Use "Ranked first under the selected objective" and never recommendation language.

## Metric comparison

A category-filtered responsive matrix presents baseline, each scenario, paired mean/relative delta, improvement probability, and confidence interval using only response evidence. Desktop uses accessible row/column headers; mobile uses stacked scenario groups. Missing or non-finite values render as Not available.

## Uncertainty

An HTML/CSS or inline-SVG interval component states lower, mean, upper, confidence level, documented normal-approximation method, and backend reliability. It is readable without colour and is not described as an outcome range or statistical significance. Improvement evidence states improved, degraded, and tied percentages plus counts when supplied.

## Risk comparison

For each returned threshold, show label, baseline and scenario violation probabilities, percentage-point difference, factual direction, and the four paired transition counts. With no threshold, state "No risk threshold configured for this metric."

## Resource comparison

For each returned resource pool, show baseline/scenario utilization, delta, idle proportion, mean request wait, maximum concurrent usage, and request count. Interpretation remains neutral. Optional factual load bands use documented presentation thresholds only and never feed ranking.

## Technical evidence

A native disclosure contains applied overrides, model hashes, seed/run/paired counts, status, objective/risk/resource/guardrail evidence, representative seed, confidence method, integrity, work metadata, and an optional collapsed raw response. Raw JSON is not the default view and internal exceptions are never shown.

## Flow visualization

Flow is available before comparison results. Structure maps the canonical source, stages, routes, completion, rework, and resource relationships through stable model IDs and deterministic frontend-only layout metadata. Scenario changes maps only explicit overrides. Operational pressure shows one selected backend-returned stage or resource metric with raw values and labelled relative intensity. Baseline vs scenario shows applicable returned values and only backend-supplied deltas. Selection opens a factual source, stage, resource, or terminal inspector. A visible semantic list mode supplies the complete non-visual equivalent. See `WORKFLOW_VISUALIZATION_SPEC.md`.

## Export

JSON contains an export version/timestamp, sanitized baseline display assumptions, scenario definitions, execution settings, comparison result, and integrity metadata. CSV contains one scenario row with returned status, rank, objective, deltas, probabilities, guardrail, paired runs, and risk. Event arrays, unsafe keys, stack traces, paths, secrets, and browser internals are excluded recursively. Print styles include the comparison summary and suppress controls.

## Empty states

Before execution, Analysis invites a comparison. Missing result sections say evidence is unavailable. No eligible scenario states "No scenario satisfied the current comparison requirements." No guardrail and no risk threshold use their exact dedicated wording.

## Failure states

Validation, work budget, baseline, scenario, paired ratio, integrity, network, timeout, abort, unexpected response, and unknown server failures use safe categories and preserve inputs. Abort and timeout differ. Retry repeats current inputs. A monotonically increasing request identity prevents stale completion from replacing newer state.

## Responsive behavior

At 1440 x 900, configuration and analysis may form two columns. At 768 x 1024 and 390 x 844, sections stack, controls wrap, matrices become scenario cards, and no page-level horizontal overflow is required. Touch targets remain reachable and print uses a linear document.

## Accessibility

Every control is labelled and unit/error help is associated. Invalid controls expose `aria-invalid`. Loading, completion, and failure are announced. Tabs implement keyboard semantics. Scenario, flow-node, mode, list, inspector, and export actions have explicit names. Tables expose captions and headers. Visual bars, intervals, risk matrices, workflow connectors, change marks, and pressure values have complete text equivalents and status is never colour-only.

## Outputs

The workspace outputs a factual overview, category-filtered comparison, uncertainty, risk, resources, per-scenario technical evidence, sanitized JSON/CSV downloads, and a printable summary backed entirely by the current response.

## Deferred capabilities

Cloud persistence/sharing, accounts, topology or arbitrary JSON editing, chart/animation libraries, playback, sweeps, optimization, costs/ROI, recommendation/LLM interpretation, workers, parallelism, multiple templates, and deployment remain deferred.
