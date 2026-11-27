# Jira / JSM data feasibility

**Verification status:** classifiers are endpoint-aware. Live Jira/JSM reads go through the Forge resolver with `asUser()`. Hosted bodies are still an acceptance gate, not assumed from unit tests.

Intended site: `https://opstwin-dev.atlassian.net`, project key `OPS`.

## Feasibility matrix

| Endpoint | Method | Scopes | Pagination | Fields requested | Failure | Live (CG-2) |
|---|---|---|---|---|---|---|
| `/rest/api/3/project/{key}` | GET | `read:jira-work` | n/a | id, key, name | 401/403/404/malformed | implemented; body gated on install |
| `/rest/api/3/project/{key}/statuses` | GET | `read:jira-work` | n/a | id, name, statusCategory | optional if 403 | implemented |
| `/rest/api/3/search/jql` | GET | `read:jira-work` | `nextPageToken` / `isLast`; missing token is incomplete | created, resolutiondate, status, priority, assignee, project, updated, labels, request-type custom field; expand changelog is never treated as a complete history | empty ≠ 403; malformed ≠ empty; ISO timestamps are not used in JQL | implemented |
| `/rest/api/3/issue/{id}/changelog` | GET | `read:jira-work` | startAt / total / isLast; offset advances by history count | status, assignee, priority, resolution items | incomplete history is never lifecycle-complete | always retrieved; expand is a hint only |
| `/rest/api/3/issue/{id}/worklog` | GET | `read:jira-work` | startAt | id, started, timeSpentSeconds (no author display name) | 403 → unknown coverage | implemented |
| `/rest/api/3/field` | GET | `read:jira-work` | n/a | request-type custom field id | optional | implemented |
| `/rest/servicedeskapi/servicedesk` | GET | `read:servicedesk-request` | start/limit | id, projectKey | empty ≠ 403 | implemented |
| `/rest/servicedeskapi/servicedesk/{id}/requesttype` | GET | `read:servicedesk-request` | start/limit | id, name | optional | implemented |
| `/rest/servicedeskapi/request/{key}/sla` | GET | `read:servicedesk-request` | n/a | cycle start/stop, elapsed millis, breached | 404 → unavailable | implemented |
| `POST /rest/api/3/changelog/bulkfetch` | POST | `read:jira-work` | nextPageToken | not used at 40-case budget | n/a | deferred |

Sources: [Jira REST v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/), [JSM REST](https://developer.atlassian.com/cloud/jira/service-desk/rest/), retrieved 2026-11-26.

Empty `issues: []` with HTTP 200 is **not** a permission failure. HTTP 401/403 is. This distinction is tested in `classify-response.test.js`.

## Parameter classes

**Observable (if live access exists):** project metadata, request types, issue created/resolved, current status, changelog, SLA cycles when licensed.

**Derived with declared bias:** arrival rate from created times; occupancy from status duration (calendar time ≠ handling time); staffing from unique assignees (not licensed agent seats).

**Assumed:** processing distributions, queue policy, failure routes, AI effectiveness without a pilot.

**Unknown until evidence exists:** true touch time, future automation quality, business-calendar SLA vs model minutes.

Do not bulk ingest or fabricate historical timestamps.
