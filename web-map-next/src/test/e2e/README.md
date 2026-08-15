# Browser end-to-end specs

These drive a real browser against a **running** SURGE stack. They are excluded from
`npm test` (see `vitest.config.ts`) because they need PostGIS, the Java backend and the Python
optimiser up — a unit run must not silently pass just because a service was unreachable.

## Running them

```bash
docker compose up -d
npm run test:e2e
```

Optional environment:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SURGE_E2E_BASE_URL` | `http://localhost:5174` | Where the web app is served |
| `SURGE_E2E_USERNAME` | `admin` | Sign-in user |
| `SURGE_E2E_PASSWORD` | `admin` | Sign-in password |
| `SURGE_E2E_PROJECT` | *(first project)* | Name of the project to exercise |

The spec skips itself with a clear message if the app is not reachable, rather than failing in a
way that looks like a product defect.

## What it covers

The path a demo actually takes: sign in, load a project, confirm assets are listed, run an
optimisation, and check the decision summary and BOM reflect that run. It deliberately asserts on
user-visible outcomes rather than internal state, because the failures worth catching here are the
ones where each service works in isolation and the seams do not.

## Known gap

Report download is not asserted. Browser download handling differs enough between drivers that a
flaky check would be worse than an honest omission; the CSV and PDF endpoints are covered by the
backend suite instead.
