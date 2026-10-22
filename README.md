# SURGE — Smart Utility Routing and Grid Evacuation

Collector-network and evacuation routing for wind farms. Import a site survey, and SURGE lays out
the 33 kV collector network that connects every turbine to the substation — feeder grouping, route
geometry over a terrain and constraint cost surface, pole placement, an electrical check, and a
bill of materials — then shows it on a map and tells you why it chose that route.

Built for a small internal engineering team. Not a hosted product.

```mermaid
flowchart LR
    U([Engineer]) --> F["Web map<br/>React · Leaflet<br/>:3000"]
    F -->|"/api/v1 via nginx"| B["Java backend<br/>Spring Boot 3.3 · Java 21<br/>:8080"]
    B <-->|"GeoJSON over HTTP"| P["Optimiser<br/>FastAPI · pandapower<br/>:8000"]
    B --> D[("PostGIS 16<br/>:5432")]
```

The frontend talks only to the backend; nginx proxies `/api/` internally, so the whole app is one
origin. The optimiser is never reached by the browser. The backend, optimiser and database ports are
published on `127.0.0.1` only (for local tools and the Vite dev server); `:3000` is the one
network-facing entry point.

---

## What it does

**Import** — Drag in a `.kmz`, `.kml`, or GeoJSON survey. Turbines, substations, evacuation towers,
reference lines, cadastral parcels and restricted areas are classified on ingest. Turbines marked
cancelled, low-AEP or to-be-shifted are stored and drawn but excluded from optimisation.

**Optimise** — Turbines are grouped into capacity-constrained feeders, a minimum spanning tree gives
each feeder its topology, and routes are traced with A\* over a cost surface built from terrain and
the site's own constraints. Poles are placed along the result and classified tangent, angle,
junction or terminal.

**Four scenarios that genuinely differ** — Balanced, Minimum Cost, Minimum Land Impact and Minimum
Environmental Impact change both the scoring weights and the constraint costs and clearances sent
to the optimiser, so they return different networks rather than the same one relabelled.

**Explain** — Every run records why its route won: the score components, the constraints it avoided,
and what it traded away.

**Report** — Network length, pole count by class, estimated capex, electrical losses from an AC load
flow, and right-of-way exposure computed from real parcel/corridor intersection. Exportable as PDF
and CSV.

**Account control and audit** — Login is required for every route. Administrators provision
accounts, reset passwords and disable users from an in-app panel, and the audit log records who did
what.

---

## Requirements

- **Docker Desktop** with Compose v2 — for the full stack
- **JDK 21**, **Python 3.11**, **Node.js 20** — only for working on a component directly

---

## Quick start

```bash
cp .env.example .env
```

Then **generate a signing key** and put it in `.env` as `APP_JWT_SECRET`:

```bash
openssl rand -base64 48
```

This is not optional — Compose refuses to start without it, deliberately. See
[Security](#security-before-you-deploy) for why.

```bash
docker compose up --build
```

Wait for all four services to report healthy, then open **http://localhost:3000**.

| Service | Health check |
| --- | --- |
| Java backend | `http://localhost:8080/actuator/health` |
| Python optimiser | `http://localhost:8000/api/v1/health` |

### First login

A fresh database seeds a single administrator from `SURGE_BOOTSTRAP_ADMIN_USERNAME` /
`SURGE_BOOTSTRAP_ADMIN_PASSWORD`. **The password has no default:** on a fresh database the backend
refuses to start unless you set one (at least 8 characters, and not `admin`). Put it in `.env`
before the first start. An existing database already has the account and needs neither. Every other
account is created by an administrator from inside the app; nothing here overwrites a password that
already exists, so credentials you change survive a restart.

To try it without a survey of your own, use the **Download Sample .KMZ** link in the Assets tab and
import the file it gives you.

---

## Working on it

### Web map

```bash
cd web-map-next && npm ci && npm run dev
```

> **Two builds serve this app and they do not update together.**
>
> - `http://localhost:3000` — the `frontend` container, serving a bundle baked at image build
>   time. It does **not** pick up source edits.
> - `http://localhost:5173` — the Vite dev server above, with hot reload.
>
> After changing anything under `web-map-next/src`, rebuild the container before testing on 3000:
>
> ```bash
> docker compose up -d --build frontend
> ```
>
> This has already caused a fix to be reported as working on 5173 while 3000 still served the
> broken version. Verify on the port you actually intend to use.

### Java backend

```bash
cd backend-java && ./mvnw verify
```

### Python optimiser

```bash
cd optimisation-python
py -3.11 -m venv .venv && .venv/Scripts/activate
python -m pip install -r requirements.lock.txt
python -m ruff check app tests && python -m mypy app && python -m pytest -q
```

---

## Testing

| Suite | Count | Command |
| --- | --- | --- |
| Java backend | 290 | `./mvnw verify` |
| Python optimiser | 601 | `python -m pytest -q` |
| Web map | 144 | `npm run test` |

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs all three plus `docker compose build`
on every push and pull request.

Security-relevant behaviour is covered deliberately rather than incidentally. `SecurityBoundaryTest`
exercises the real filter chain — every other controller test disables filters, so none of them
could catch an accidental `permitAll`.

---

## Security: before you deploy

This runs safely on a laptop. Before it is reachable from the internet, see
[§5.7 of the gap closure plan](docs/MVP%20Gap%20Closure%20Plan.md) and:

1. **TLS.** nginx serves plain HTTP and tokens travel in headers, so whatever sits in front must
   terminate TLS.
2. **Replace the example values.** `.env.example` ships `DB_PASSWORD=postgres`; Compose requires the
   variable but not that it be strong.
3. **Treat the login throttle as a speed bump.** Five failed sign-ins from one client address in
   15 minutes lock that address out for 15 minutes (HTTP 429). The counter is in memory, so it
   assumes a single backend replica, and the address is whatever nginx reports: behind a tunnel or
   another proxy, configure nginx's real-IP handling, and rate-limit at the edge.

Already handled: the bootstrap administrator and the JWT signing key have no defaults and the
backend refuses to start without them; the authentication filter resolves the account behind every
token, so disabling, demoting or resetting a user takes effect immediately rather than whenever
their token expires.

Known open issues are listed in [`docs/Project Review.md`](docs/Project%20Review.md) — notably that
only administrators are distinguished by role (a viewer can still change data), that the audit log
is readable by every signed-in user, and that the upload path and export endpoints have had a
read-through review, not a penetration test. Fine behind a VPN; not fine on a public URL holding
client survey data.

---

## Documentation

- [`CONTEXT.md`](CONTEXT.md) — implementation status and the full progress record
- [`docs/MVP Gap Closure Plan.md`](docs/MVP%20Gap%20Closure%20Plan.md) — the living plan, with what
  each piece of work actually produced and what it got wrong
- [`docs/MVP - Minimum Viable Product.md`](docs/MVP%20-%20Minimum%20Viable%20Product.md) — scope
- [`docs/Python Engine - Architecture.md`](docs/Python%20Engine%20-%20Architecture.md) — optimiser internals
- [`docs/Surge MVP Ticket Plan.md`](docs/Surge%20MVP%20Ticket%20Plan.md) — the SURGE-PY ticket sequence
- [`docs/Project Review.md`](docs/Project%20Review.md) — completeness, known flaws and stale-doc audit
- `obsidian-vault/` — design notes and research
