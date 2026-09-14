# Surge Repository Guide

## Scope

- Default ownership is `optimisation-python/`. Read other components to trace contracts, but do not modify `backend-java/`, `web-map-next/`, `web-map/`, or `database/` unless the user explicitly requests it.
- When changing technical documentation represented in both `docs/` and `obsidian-vault/`, update both copies; `docs/Surge MVP Ticket Plan.md` is authoritative for Python ticket boundaries.

## System Boundaries

- The deployed path is `web-map-next/` (React/Leaflet) -> `/api/v1` -> `backend-java/` (Spring Boot) -> `/api/v1/optimise` -> `optimisation-python/` (FastAPI). The browser must not call the optimiser directly.
- `web-map/` is the retired vanilla-JS frontend. It is retained for reference and is not built by Compose or CI.
- Python exposes V1 and V2 APIs, but Java still consumes V1. V1 maps through `app/schemas/legacy_mapping.py` into the shared `app/optimisation/orchestrator.py`; preserve that compatibility path unless Java is deliberately migrated too.
- Runtime schema changes belong in new Flyway migrations under `backend-java/src/main/resources/db/migration/`. `database/init.sql` is empty and is not mounted by Compose.
- The frontend API layer is `web-map-next/src/lib/api/`; server state uses TanStack Query, UI/auth state uses Zustand, and map rendering is centralized in `src/lib/map/SurgeMapEngine.ts`.

## Toolchains And Setup

- CI pins Java 21, Python 3.11, and Node 20. `web-map-next/package.json` additionally requires Node `>=20.18.0`.
- Install Python dependencies from `optimisation-python/requirements.lock.txt` into `optimisation-python/.venv`; `requirements.txt` is not the CI input.
- Use `npm ci` in `web-map-next/`; both frontend directories have independent `package-lock.json` files.
- Compose interpolation requires `DB_PASSWORD` and `APP_JWT_SECRET`. A fresh database also refuses to seed without a non-default `SURGE_BOOTSTRAP_ADMIN_PASSWORD` of at least eight characters. Start from `.env.example`, but fill its blank bootstrap password.

## Verification Commands

Run commands from the named component directory.

### Python (`optimisation-python/`)

- CI sequence: `python -m ruff check app tests`, then `python -m mypy app`, then `python -m pytest -q`.
- Focus a file or case with `python -m pytest tests/test_route_refinement.py -q` or `python -m pytest tests/test_route_refinement.py::test_name -q`.
- Ruff uses an 88-column limit; mypy is strict and checks `app/`, not tests.
- Local server: `python -m uvicorn app.main:app --reload --port 8000`. OpenAPI/docs are disabled when `ENVIRONMENT=production`.

### Java (`backend-java/`)

- CI-equivalent suite: `./mvnw verify --batch-mode` (PowerShell: `.\mvnw.cmd verify --batch-mode`).
- Focus a class with `./mvnw -Dtest=SecurityBoundaryTest test` (PowerShell: `.\mvnw.cmd -Dtest=SecurityBoundaryTest test`).
- Most controller tests disable Spring Security filters. Any authorization change must also exercise `SecurityBoundaryTest`, which loads the real filter chain.

### Frontend (`web-map-next/`)

- CI sequence after `npm ci`: `npm run test`, then `npm run build`; build runs `tsc --noEmit` before Vite. There is no lint script.
- Focus a Vitest file with `npm run test -- src/lib/api/client.test.ts`.
- `npm run test:e2e` is excluded from unit tests and requires a running database, backend, optimiser, and frontend. Confirm Playwright actually ran: the spec intentionally skips when the app is unreachable.

### Full Stack

- CI only builds images: `docker compose build`. Local startup is `docker compose up --build` after populating `.env`.
- Compose serves the baked frontend at `http://localhost:3000`; source edits do not appear there until `docker compose up -d --build frontend`.
- `npm run dev` uses port 5173 and proxies `/api` to port 8080. Playwright defaults to port 5174, so set `SURGE_E2E_BASE_URL=http://localhost:5173` for Vite or `http://localhost:3000` for Compose.

## Test And Contract Notes

- Python API fixture payloads live in `optimisation-python/tests/fixtures/`; V1 and V2 endpoint coverage is under `tests/api/`.
- Optimisation runs are asynchronous in Java but the Java-to-Python POST is synchronous inside the worker. Preserve the separate `OptimizationJobRunner` bean: Spring `@Async` would not apply to self-invocation.
- The worker must read a committed job row before execution; transaction changes around job creation/submission can otherwise make jobs disappear to the async thread.

# SURGE Codex Role

Codex is responsible for:

- implementation verification;
- defect diagnosis;
- minimal repairs;
- regression protection;
- implementation-level code review.

Codex is NOT the primary architecture-design authority.

Architecture and ticket design are established upstream.

Do not silently redesign approved architecture during testing, repair, or review.

If repository evidence demonstrates that the approved architecture cannot work,
report an ARCHITECTURE BLOCKER instead of inventing a replacement design.

---

## Code Review Rules

When performing `/review`, act as an independent implementation reviewer.

Review the implementation against:

1. current code contracts;
2. tests;
3. ticket requirements when available;
4. SURGE architectural invariants.

Prioritize real engineering problems over stylistic preferences.

### Look for correctness defects

Flag:

- incorrect calculations;
- incomplete implementations;
- incorrect state propagation;
- hidden placeholders;
- hard-coded fake values;
- stale derived state;
- broken fallback behavior;
- incorrect aggregation;
- partial contract implementation.

### Look for semantic contract defects

Pay special attention to:

- None vs zero;
- unavailable vs empty;
- unmeasured vs measured;
- failure vs not evaluated;
- fallback vs authoritative result;
- candidate-local vs global state.

Do not allow presentation or reporting layers to fabricate engineering truth.

### Preserve deterministic behavior

Flag:

- unstable ordering;
- implicit nondeterminism;
- incomplete cache fingerprints;
- unstable tie breaking;
- unordered candidate generation;
- hidden mutable state.

### Preserve candidate failure isolation

One invalid candidate must not crash or corrupt unrelated candidate evaluation.

Flag:

- shared mutable state;
- exceptions escaping candidate boundaries incorrectly;
- contamination between candidate evaluations;
- fallback state reused incorrectly.

### Canonical evaluation

Do not allow alternative search, reporting, ML, or optimization paths to establish
a second definition of engineering truth.

Search-generated candidates must pass through the canonical evaluation path.

### Electrical authority

Pandapower and established engineering validation remain authoritative for
electrical feasibility.

Flag logic that bypasses or falsifies electrical validation.

### Tests

Flag when:

- regression tests are missing;
- only happy paths are covered;
- assertions are too weak;
- tests verify implementation details instead of behavior;
- tests were weakened to make implementation pass;
- mocks hide production behavior.

### Scope

Flag unrelated refactoring when it:

- increases regression risk;
- obscures the actual implementation;
- changes unrelated public behavior.

Do not report harmless formatting differences as engineering defects.

### Severity

Classify findings as:

BLOCKER
HIGH
MEDIUM
LOW

Do not inflate severity.

Every material finding must include:

- location;
- evidence;
- affected behavior;
- failure scenario;
- recommended correction direction.

### Architecture boundary

If the implementation conflicts with an approved architecture decision:

REPORT the mismatch.

Do not redesign the architecture during review.

Use:

ARCHITECTURE MISMATCH

and describe:

- expected contract;
- implementation behavior;
- evidence;
- affected components.

### Review Verdict

End with exactly one:

APPROVE

APPROVE WITH NON-BLOCKING NOTES

CHANGES REQUIRED

BLOCK