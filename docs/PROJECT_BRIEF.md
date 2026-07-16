# OpsTwin Project Brief

## Name and pitch

**OpsTwin** is a digital twin-style operational simulation and decision laboratory for testing changes to business workflows before applying them. It is not yet a live synchronized digital twin.

## Problem

Service leaders make staffing, routing, and process decisions using spreadsheets, averages, and intuition that hide queues and variability.

## Primary user and story

The primary user is a service-operations leader or analyst. They need to model a workflow, run repeatable scenarios, and understand bottlenecks so they can recommend interventions with traceable evidence.

## Current workaround

Teams combine spreadsheets, manual process maps, BI reports, and bespoke analysis; assumptions and metric definitions are difficult to reproduce.

## Success definition and initial metrics

Success means a user can encode a supported operation, reproduce mathematically validated results, compare a future scenario, and explain the difference. Initial measures are model completion rate, agreement with golden models, reproducibility, time to first result, and user confidence in explanations.

## MVP scope

- Service-operation models with arrivals, FIFO queues, stages, resources, and explicit units.
- Validated discrete-event runs and interpretable operational metrics.
- Saved baselines, parameterized scenarios, comparisons, and bottleneck evidence.
- A usable workflow configuration and results experience.

## Explicit non-goals

Sprint 00 excludes live synchronization, authentication, persistence, Monte Carlo, scenario comparison, workflow editing, recommendations, animation, and deployment infrastructure.

## Constraints

Correctness precedes visual scope. The system is a pnpm monorepo with Next.js and a separate Python FastAPI/SimPy service. It must stay runnable without external services during foundation work. The future public boundary is one Vercel project, but deployment is not configured yet.

## Risks and assumptions

Risks include ambiguous operational semantics, misleading aggregate metrics, and premature interface scope. Assumptions are that service teams can provide defensible inputs, FIFO is a useful first discipline, and normalized events can support metrics, debugging, and later playback.

## First operational template

Customer-support triage: fixed arrivals enter one FIFO queue and one capacity-constrained stage, then complete against a cycle-time SLA.

## Delivery milestones

Foundation and deterministic proof; stochastic kernel; metric validation; API and persistence; first usable slice; scenarios; uncertainty; visual studio; playback; sensitivity; recommendations; polish and deployment.
