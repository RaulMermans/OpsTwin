# ADR-002: Python simulation service

- Status: accepted

## Context

Simulation correctness benefits from a mature scientific ecosystem, while the product interface benefits from TypeScript.

## Decision

Keep simulation logic in Python, separated from the TypeScript frontend.

## Options considered

Python service; TypeScript-only monolith; simulation in the browser; another compiled service.

## Rationale

Python provides SimPy and strong analysis tooling while a contract boundary prevents simulation logic from leaking into presentation code.

## Consequences

The repository has two runtimes and must maintain typed contracts and aligned CI checks.

## Revisit triggers

Measured deployment or performance constraints outweigh ecosystem value, or the boundary creates unacceptable operational cost.

## Validation plan

Run deterministic simulation tests independently of the web app and validate shared JSON examples.
