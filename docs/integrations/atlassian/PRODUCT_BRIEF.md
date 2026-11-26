# OpsTwin for Jira — product brief

**Product:** OpsTwin for Jira — AI Transformation Lab  
**Tagline:** Simulate before you automate.  
**Parent:** OpsTwin (`https://ops-twin.vercel.app`, MIT, public GitHub `RaulMermans/OpsTwin`)  
**Competition:** Atlassian Codegeist 2026, intended category **Apps for Business Teams**  
**Access dates:** official Codegeist pages retrieved 2026-11-26

## Problem

JSM teams can add agents, virtual agents, or automation and still not know whether a faster local task improves the operation. Queues, rework, review load, and cost interact. Dashboards describe the past. Native AI features report deflection and handle time, not matched counterfactual operations.

## Intended users

Operations, support, and IT service owners using Jira Service Management who must decide whether to staff, automate, or hybridize a workflow before changing production.

## Narrative constraint

Demonstration claim: **a faster task does not necessarily mean a better operation.** Results must come from the existing simulation engine. Do not manipulate outputs to force the story.

## In-product surface

A Forge `jiraServiceManagement:queuePage` (and compatible `jira:projectPage`) named **OpsTwin for Jira**. CG-0 is an installability stub. The later lab will import project evidence, show missing assumptions, and run paired scenarios.

## Non-goals for the Codegeist slice

ServiceNow/Zendesk connectors, Rovo agents as the primary product, rewriting SimPy, Marketplace publication in CG-0, production releases of the standalone app as an Atlassian dependency.
