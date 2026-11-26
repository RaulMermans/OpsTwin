# OpsTwin for Jira (Forge)

Atlassian application layer for **OpsTwin for Jira — AI Transformation Lab**.

This package is isolated from OpsTwin Core. The simulation engine remains in `apps/simulation-api` and must never import Forge modules.

## Status (CG-0)

- Local Custom UI and resolver foundation: implemented
- Official app identity: `ari:cloud:ecosystem::app/73670daa-a329-4491-8a96-89bf239b203b` in Developer Space **OpsTwin**
- Live install on `opstwin-dev.atlassian.net`: in progress after CG-0 register

Do not invent or reuse another product's Forge app ID. Do not deploy the placeholder identity.

## Commands

```sh
cd apps/atlassian-forge
npm install
npm --prefix static/transformation-lab install
npm test
npm run build
```

After authentication (owner-run, interactive):

```sh
forge login
forge register
forge lint
forge deploy
forge install --site opstwin-dev.atlassian.net --product jira
```

Install only on the dedicated development site. Do not publish to Marketplace from this sprint.
