# ADR-001: Service operations as the initial wedge

- Status: accepted

## Context

OpsTwin needs a focused domain whose queueing behavior is valuable and understandable without production-system complexity.

## Decision

Start with support, claims, onboarding, and back-office workflows rather than production, inventory, or logistics.

## Options considered

Service operations; manufacturing; inventory and logistics; a domain-neutral editor from day one.

## Rationale

Service flows expose arrivals, queues, capacity, SLAs, and rework while keeping the initial data and UI surface bounded.

## Consequences

Early templates and validation prioritize service semantics. The engine remains capable of later generalization without promising it now.

## Revisit triggers

Validated demand is stronger in another domain, or service assumptions block a general engine capability.

## Validation plan

Test the support-triage golden model and conduct future discovery with service-operations users.
