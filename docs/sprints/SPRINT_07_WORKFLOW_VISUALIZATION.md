# OpsTwin Sprint 07 — Controlled Workflow Visualization

## Objective

Add a deterministic, read-only operational-flow view to Scenario Lab so users can understand structure, explicit scenario changes, and returned evidence before interpreting comparison tables.

## Current Scenario Lab baseline

Sprint 06 provides baseline assumptions, up to three controlled scenarios, comparison execution, factual result views, exports, and responsive controls. Sprint 06.1 confirms source lint and typecheck pass, while test startup, build completion, API temp-dependent cases, and browser QA remain blocked by the managed Windows process/filesystem environment.

## In scope

- Canonical source, stage, route, terminal, rework, and resource relationships.
- Stable frontend-only presentation metadata and deterministic layout.
- Structure, Scenario changes, Operational pressure, and Baseline vs scenario modes.
- Selection, factual evidence inspector, semantic list equivalent, and responsive fallback.
- Pure mapping, change-targeting, and display-scaling functions with focused tests.

## Out of scope

- Workflow editing, drag-and-drop, topology mutation, persisted layout, animation, graph libraries, new backend metrics, scoring, advice, and deployment.

## Model-to-visual mapping

Operational IDs remain the identity source. Sources and stages map one-to-one. Route options map to stable edges; completion targets receive deterministic presentation-only terminal IDs. Resource pools map to selectable resource nodes and stage-resource links. Unknown references produce warnings and omitted invalid links rather than a workspace crash.

## Layout strategy

The canonical support template uses explicit frontend-only row, column, lane, and order metadata. Rendering uses semantic controls in CSS Grid plus a decorative SVG connector layer. Structure and positions do not change with scenario selection or evidence overlays. Unknown nodes receive a stable fallback order.

## Scenario-change strategy

Only explicit scenario overrides identify changed entities. Override entity type and ID map to a source, stage, resource, route, or SLA evidence record. Values are presented factually. Arbitrary serialized model diffs are not used.

## Overlay strategy

Stage and resource values come directly from baseline or selected scenario aggregates returned by the API. A pure display function scales visible finite values from 0 to 1, maps equal values to 0.5, and preserves unavailable values. Raw values and the label “Relative intensity within the current result” accompany colour/intensity.

## Accessibility strategy

Nodes are keyboard-operable buttons with descriptive names, visible selection, and a closeable inspector. A semantic visible list/table equivalent describes routes, resource assignments, changes, and overlay values. Connectors are decorative because relationships are present in text. Escape clears selection and closing the inspector restores node focus.

## Responsive behavior

Desktop uses the controlled multi-lane grid with a side inspector. Tablet reduces spacing and allows the inspector to move below. Mobile hides the connector layer and uses a single ordered vertical flow without required horizontal panning.

## Test plan

- Exact canonical mapping, stable layout/order, terminal and rework relationships, immutability, duplicate/reference safety.
- Explicit override targeting and unchanged-entity behavior.
- Exact overlay scaling for finite, equal, missing, and non-finite values.
- Selection, inspector, mode/scenario switching, clearing, focus restoration, and failed-result states.
- Semantic flow/list coverage and prohibited product-language checks.

## Verification limits

The current runtime permits lint and TypeScript checks. Vitest cannot load its Vite config because child process creation returns `EPERM`. Next compiles then fails spawning its type worker, and `next dev` cannot spawn. Browser and viewport QA therefore remain blocked until the environment changes.

## Acceptance criteria

- The complete canonical workflow and resources map without mutating input.
- Layout is stable and remains fixed across modes.
- Explicit scenario targets and only those targets are marked.
- Returned evidence is shown with raw values and bounded presentation intensity.
- Selection and factual inspection work for source, stage, resource, and terminal entities.
- Flow is available before execution; result-dependent modes explain unavailable evidence.
- A semantic textual equivalent and mobile fallback exist.
- Existing Scenario Lab and backend contracts remain unchanged.

## Definition of done

Source, tests, specifications, ADRs, project verification skill, golden-model definitions, and local evidence are present. Runtime-only gates remain explicitly blocked rather than inferred as passing.

## Rollback plan

Remove the single Scenario Lab integration point while retaining isolated mapper/tests for diagnosis. Reintroduce structure, changes, overlays, and inspector incrementally. Do not change backend contracts or introduce a graph dependency as a workaround.
