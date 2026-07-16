# Workflow Visualization Specification

## Purpose

Explain the operational model and connect scenario assumptions to returned evidence through a deterministic, read-only view.

## User

An operations analyst who needs to understand where work enters, how it moves, which resources support it, where rework occurs, and what evidence differs for a controlled scenario.

## Input model

The input is the existing operational-model object plus optional explicit scenario overrides and optional comparison response. The input remains immutable and the simulation schema is not extended.

## Presentation metadata

Frontend-only metadata supplies canonical row, column, lane, order, and optional edge-path preferences. It never enters simulation requests. Missing metadata uses a deterministic fallback.

## Nodes

Sources, stages, resources, and presentation-only terminal outcomes become uniquely identified selectable nodes with stable IDs, labels, kinds, positions, associated resource IDs, and accessible descriptions.

## Edges

Each valid route option becomes a stable directed edge from its stage to a stage or terminal. Invalid references are omitted with a warning. Duplicate visual IDs invalidate the mapping safely.

## Routes

Route kind, probability, and source route ID are preserved for factual labels and inspection. Edges do not replace the semantic relationship list.

## Resource relationships

Each stage’s `resourcePoolId` creates a presentation link to the matching resource node. Unknown pools produce warnings. Resource capacity and supported-stage relationships appear in inspection and list views.

## Completion

Completion route options map to deterministic terminal nodes using route identity and option index, without creating simulation IDs.

## Rework

Failure routes and stage failure route references are marked as rework. They receive a distinct visual treatment and explicit semantic text.

## Layout

The support template uses stable controlled metadata. CSS Grid places semantic node controls; an inline decorative SVG draws connectors. Modes, selection, scenario names, and metrics never move nodes. Mobile uses stable ordered vertical flow.

## Baseline mode

Structure mode shows the complete baseline topology, resources, route probabilities, and compact assumptions before a comparison exists.

## Scenario mode

Scenario changes mode marks entities referenced by the selected scenario’s explicit overrides and lists entity, field, baseline value, scenario value, and direction.

## Comparison mode

Baseline vs scenario shows applicable backend-returned baseline and selected scenario values. A delta is shown only when the backend supplies it. Failed or absent scenarios produce a factual unavailable state.

## Change overlays

Override entity type and ID determine targets. Source, stage, resource, route, and SLA targets are supported. Renaming or duplicating a scenario does not change target detection. Unknown targets become warnings.

## Pressure overlays

Supported stage evidence is average waiting time, time-weighted queue length, failure rate, rework count, and visit count. Supported resource evidence is utilization, idle proportion, mean request wait, and maximum concurrent usage. Missing evidence remains unavailable and no combined operational score is created.

## Selection

One entity is selected at a time. Selection persists across modes and scenarios when its ID remains valid. Escape or Close clears selection; Close restores focus to the previously selected node. Unknown selections clear safely.

## Evidence inspector

The inspector shows structure, assumptions, resource relationships, routes, failure/rework configuration, explicit changes, returned aggregates, supplied deltas, and evidence availability appropriate to the selected entity kind. Copy is factual.

## Accessibility

Nodes use semantic buttons and descriptive accessible names. Selection is expressed in state and text as well as colour. Relationships, changes, and overlay values have semantic list/table equivalents. Decorative SVG connectors are not focusable. Reduced-motion mode has no required animation.

## Responsive fallback

At desktop width the map is multi-lane with an adjacent inspector. Tablet may place the inspector below. At mobile width the visual becomes an ordered vertical list, connectors are hidden, tap targets remain usable, and no horizontal panning is required.

## Empty states

No model, no scenarios, no selected metric, equal values, and all-unavailable values each have explicit factual states. Structure remains usable without results.

## Failure states

Invalid mapping, unknown route or resource references, unknown override targets, missing entity metrics, and failed scenarios never crash the workspace. Warnings identify unavailable presentation evidence without altering requests.

## Outputs

The module outputs a typed presentation object, explicit change records, presentation-only overlay intensity, the visual map, an evidence inspector, and a semantic list equivalent. None are simulation inputs or ranking fields.

## Deferred editing capabilities

Topology editing, node movement, automatic graph layout, persisted positions, workflow creation, and any general graph-editor dependency are deferred.
