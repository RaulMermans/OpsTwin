# Security Policy

## Supported version

OpsTwin does not maintain multiple released versions. The only supported
target is the code currently on `master` and the production deployment it
drives at `https://ops-twin.vercel.app`. There is no long-term-support
branch and no backport policy.

## Scope

In scope: the Next.js web application (`apps/web`), the FastAPI simulation
service (`apps/simulation-api`), the JSON Schema contracts (`contracts/`),
and the Vercel deployment configuration (`vercel.json`, `.vercelignore`).

Out of scope: the underlying platforms this project depends on (Vercel,
GitHub, Node.js, Python, and their respective supply chains) — report those
to their own maintainers. OpsTwin has no database, authentication system,
or user accounts, so account-takeover and data-exfiltration reports specific
to those categories do not apply; a report that assumes their existence
likely reflects a misunderstanding of the architecture (see
`docs/ARCHITECTURE.md`) rather than a real finding.

## Reporting a vulnerability

Prefer **GitHub private vulnerability reporting** (the "Report a
vulnerability" action under this repository's Security tab), where
available for the repository's current visibility setting. If that option
is not available to you, use the reporting channel below:

<!-- OWNER ACTION: add a private reporting contact (e.g. a monitored email
address or a GitHub security advisory link) here before treating this
project as publicly reportable. Do not invent one in the meantime. -->

## What to include

- A clear description of the issue and its potential impact.
- Steps to reproduce, including request/response examples where relevant.
- The affected route, file, or contract version.
- Whether the issue was found against the production deployment, a local
  build, or by source inspection only.

## Responsible disclosure

Please do not publicly disclose an unresolved report (issue, pull request,
social media, or otherwise) until it has been addressed or you have agreed
on a disclosure timeline with the maintainer. This is a solo-maintained
portfolio project: there is no dedicated security team, no bug-bounty
program, and no guaranteed service-level agreement.

## Acknowledgement target

The maintainer aims to acknowledge a good-faith report within **5 business
days**. This is a target, not a contractual commitment, and continuous
support is not guaranteed.
