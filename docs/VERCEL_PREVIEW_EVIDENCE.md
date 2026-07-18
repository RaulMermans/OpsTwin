# Vercel Preview Evidence

## Status

Preview validation is deferred by explicit user instruction. On 2026-07-16, Vercel CLI `56.2.0` running Node.js `24.14.0` reported no stored credentials; the login flow was not completed. No preview or production deployment was created, and no further remote action should be attempted until the user provides deployment instructions.

## Local Services evidence

`vercel dev -L` recognized both configured services (`web` as Next.js and `simulation` as FastAPI) and selected `http://localhost:3001` because port 3000 was occupied. The Windows Python runner then generated `vc_init_dev.py` with an unescaped `C:\Users\...` entry path; Python rejected `\U` as a truncated Unicode escape. This is a local Vercel CLI path-generation blocker, not a FastAPI import or application error.

The documented separate-process fallback was tested at `http://localhost:3000` with a development-only same-origin rewrite to FastAPI on port 8000:

- `/`: 200, 291 ms, 19,315 bytes.
- `/workspace`: 200, 121 ms, 20,108 bytes.
- health: 200, 17 ms, 50 bytes.
- single summary: 200, 2,406 ms, 3,858 bytes.
- repeated two-run summary: 200, 356 ms, 27,678 bytes.
- 10-run, one-scenario comparison: 200, 1,535 ms, 224,312 bytes.
- invalid comparison: structured 422, 325 bytes.
- over-budget comparison: structured 422, 193 bytes.

Local timings are development evidence only and are not hosting capacity claims.

## Browser evidence

The in-app browser completed landing-to-workspace navigation, health readiness, canonical 50-run comparison, factual ranking, inline invalid-input handling, 30,000-unit work guard, mobile layout measurement, and technical-evidence disclosure. Integrity passed 16 checks. At 390 by 844 CSS pixels, final document width was 375 pixels with no horizontal overflow. Browser error/warning logs were empty.

## Preview record

- Deployment type: preview only; not created.
- Preview URL: not created; remote deployment is deliberately deferred.
- Cold/warm health and comparison timing: not measured.
- Preview payload, hash, structured-error, and browser-console replay: not measured.
- Production: not attempted and not authorized.

ADR-014 therefore remains proposed and GM-051 remains deferred.

## 2026-07-18 addendum

Local Vercel configuration was reviewed and prepared (see `docs/VERCEL_DEPLOYMENT.md` — "Deployment preparation status") without attempting `vercel login`, linking, or a new preview. No new evidence was collected in this entry; the prior 2026-07-16 record above remains the last executed evidence.
