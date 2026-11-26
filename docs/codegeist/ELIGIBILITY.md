# Codegeist 2026 eligibility

Sources retrieved **2026-11-26**:

- https://codegeist2026.devpost.com/
- https://codegeist2026.devpost.com/rules
- https://developer.atlassian.com/platform/forge/getting-started/
- https://developer.atlassian.com/platform/forge/remote/

## General eligibility (main prizes)

Open to individuals of majority age, teams, and organizations, with territorial exclusions (including Brazil, Quebec, Russia, Belarus, Crimea, Cuba, Iran, North Korea, Syria, Sudan, Myanmar, OFAC countries).

**Project requirement:** a Forge app integrating at least one Atlassian product/capability, in one category.

**Existing projects:** allowed if newly created, or if they existed before the submission period **and** were updated or rebuilt on Forge after the hackathon start (**2026-10-27**), with a Forge manifest and **at least one Forge module**.

OpsTwin Core existed before that date (public GitHub, production Vercel). The Forge application is the Codegeist Project. This must be disclosed on the submission form.

**Third-party / OSS:** allowed if licensed and the submission **enhances** the underlying product. MIT Core + new Forge layer matches this clause, subject to organizer interpretation.

**External backends:** Forge Remote is an official capability. It is compatible with **general** eligibility.

Deadline: **2026-12-22 12:00 pm PT** (site also states 3:00 pm EST). Internal freeze 2026-12-18, internal submit 2026-12-21.

Judging (equal 20%): Technological Implementation, Design, Potential Impact, Innovation/Idea, Presentation. Stage one is pass/fail theme + required APIs.

Submission must include public YouTube demo < 5 minutes, installation link via [Forge app sharing](https://developer.atlassian.com/platform/forge/distribute-your-apps/#start-sharing-your-app), English materials.

## Bonus eligibility (separate)

| Bonus | Requirement | OpsTwin CG architecture |
|---|---|---|
| Best Agents | `rovo:agent` / connector / reusable skill-action | **Not planned as P0** |
| Best app with Atlassian MCP | Forge app exposing `rovo:mcp` | **Not planned as P0** |
| Teamwork Graph | ingest and/or consume TWG API | **Not planned as P0** |
| Marketplace published | listed or submitted for listing | **After live app**, not CG-0 |
| Runs on Atlassian | no Remote / external compute | **Ineligible if we keep Python Remote** |

Do not advertise Runs on Atlassian.

## Unresolved (do not send without owner authorization)

Prepared organizer question:

> OpsTwin is existing MIT open-source discrete-event simulation software with a public Vercel app. For Codegeist we are building a new Forge app that reads JSM data and calls that engine through Forge Remote. Please confirm: (1) this satisfies the “existing project updated on Forge” rule if we disclose the pre-existing engine; (2) Forge Remote to our own simulation service remains eligible for the main category prizes even though it is ineligible for Runs on Atlassian.

Contact listed on the hackathon site: janet@devpost.com
