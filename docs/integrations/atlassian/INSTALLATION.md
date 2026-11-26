# Installation (development)

## Workstation

Verified 2026-11-26 on this host:

- Ubuntu 26.04.1 LTS, kernel 7.0.0-44-generic
- AMD Ryzen AI MAX+ 395 (32 threads)
- Node.js v22.23.4 (nvm) — matches Forge CLI requirement of 22.x ≥ 22.23.4 or 24.x ≥ 24.22.1 ([getting started](https://developer.atlassian.com/platform/forge/getting-started/), 2026-11-26)
- pnpm 11.7.0, npm 10.9.9
- Python 3.12.16 via `~/.local/bin/python3.12` (Core requires `>=3.12,<3.13`; system `python3` is 3.14.4 and must not be used for `pnpm bootstrap`)
- uv 0.13.7, Git 2.53.0
- Forge CLI **15.1.0** (CLI warned 16.0.0 is current; left unchanged per non-disruptive policy)

Bootstrap:

```sh
PYTHON=/home/raul-mermans/.local/bin/python3.12 pnpm bootstrap
```

## Forge login (owner)

1. Create a scoped Atlassian API token at https://id.atlassian.com/manage-profile/security/api-tokens (`Create API token with scopes`, app **Forge**).
2. In a local terminal, not chat: `forge login`
3. Confirm `forge whoami` shows the intended account.
4. `forge developer-spaces list` and select or create a Developer Space for OpsTwin (do not reuse RE:VERSE).
5. From `apps/atlassian-forge`: `forge register` then `forge deploy` and `forge install --site opstwin-dev.atlassian.net --product jira`

Verified 2026-11-26 after owner login and OpsTwin Developer Space:

- Account: Raul Mermans (`raulmermans@gmail.com`)
- Developer Space: `OpsTwin` (`b144a472-f1b4-484e-ae81-d0035e1f75da`)
- App: `ari:cloud:ecosystem::app/73670daa-a329-4491-8a96-89bf239b203b`
- Development deploy: success
- Install: `opstwin-dev.atlassian.net` / Jira / development, installation `b1bb872d-ce8d-4b4a-ba6b-d61fcd61b815`
- Queue page: `/jira/servicedesk/projects/OPS/queues/apps/73670daa-a329-4491-8a96-89bf239b203b/4b3fdf0a-e3f3-4589-a7ce-97b7098982db`

Payment method was **not** added. Marketplace and production app environment were **not** installed.

## Skills / MCP

Project-scope install (already applied):

```sh
forge skills install --agent cursor claude --scope project
```

Installed skills: `forge-app-builder`, `forge-app-review`, `forge-connector`, `forge-cost-optimizer`, `forge-debugger`, `forge-onboarding`, `forge-security-review`.

MCP config: `.cursor/mcp.json` and `.mcp.json` pointing at official `https://mcp.atlassian.com/v1/forge/mcp` and ADS public MCP. A new agent session is required to load them. This CG-0 session could not invoke those MCP tools.
