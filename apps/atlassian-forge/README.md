# OpsTwin for Jira (Forge)

Atlassian application layer for **OpsTwin for Jira — AI Transformation Lab**.

This package is isolated from OpsTwin Core. The simulation engine remains in `apps/simulation-api` and must never import Forge modules.

## Status (CG-2)

Operational snapshots (`os.1.0.0`) are produced inside the resolver with `asUser()`. The CG-1 synthetic comparison remote is unchanged.

## Status (CG-1)

- Official app identity: `ari:cloud:ecosystem::app/73670daa-a329-4491-8a96-89bf239b203b` in Developer Space **OpsTwin**
- Live development install on `opstwin-dev.atlassian.net`
- Remote: `opstwin-simulation` → `https://ops-twin.vercel.app/api/integrations/atlassian/v1/compare`

Do not invent or reuse another product's Forge app ID. Do not deploy the placeholder identity.

## Commands

```sh
cd apps/atlassian-forge
npm ci
npm --prefix static/transformation-lab ci
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
