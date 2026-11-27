# Jira / JSM data feasibility

**Verification status:** classifiers are endpoint-aware. Live Jira/JSM reads go through the Forge resolver with `asUser()`. Hosted bodies are still an acceptance gate, not assumed from unit tests.

Intended site: `https://opstwin-dev.atlassian.net`, project key `OPS`.

## Feasibility matrix

| Endpoint | Scopes | Fields of interest | Pagination | Privacy | Modeling | Live |
|---|---|---|---|---|---|---|
| `GET /rest/api/3/project/{key}` | `read:jira-work` | key, name, projectTypeKey | n/a | low | provenance | blocked |
| `GET /rest/api/3/project/{key}/statuses` | `read:jira-work` | status names | n/a | low | stage proxy | blocked |
| `GET /rest/api/3/search/jql` | `read:jira-work` | key, created, resolved, status, issuetype | nextPageToken | medium — restrict fields | arrivals, WIP | blocked |
| `GET /rest/api/3/issue/{id}/changelog` | `read:jira-work` | status transitions | yes | medium | occupancy, reopen | blocked |
| `GET /rest/api/3/issue/{id}/worklog` | `read:jira-work` | time spent | yes | high (author) | handling time | blocked |
| `GET /rest/servicedeskapi/servicedesk` | `read:servicedesk-request` | service desk id | yes | low | desk identity | blocked |
| `GET /rest/servicedeskapi/servicedesk/{id}/requesttype` | `read:servicedesk-request` | request types | yes | low | class mix | blocked |
| `GET /rest/servicedeskapi/request/{key}/sla` | `read:servicedesk-request` | cycle, breached, goal | n/a | medium | SLA vs sim time | blocked |
| Permissions `/mypermissions` | `read:jira-work` | BROWSE_PROJECTS | n/a | low | distinguish 403 vs empty | blocked |

Sources: [Jira REST v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/), [JSM REST](https://developer.atlassian.com/cloud/jira/service-desk/rest/), retrieved 2026-11-26.

Empty `issues: []` with HTTP 200 is **not** a permission failure. HTTP 401/403 is. This distinction is tested in `classify-response.test.js`.

## Parameter classes

**Observable (if live access exists):** project metadata, request types, issue created/resolved, current status, changelog, SLA cycles when licensed.

**Derived with declared bias:** arrival rate from created times; occupancy from status duration (calendar time ≠ handling time); staffing from unique assignees (not licensed agent seats).

**Assumed:** processing distributions, queue policy, failure routes, AI effectiveness without a pilot.

**Unknown until evidence exists:** true touch time, future automation quality, business-calendar SLA vs model minutes.

Do not bulk ingest or fabricate historical timestamps.
