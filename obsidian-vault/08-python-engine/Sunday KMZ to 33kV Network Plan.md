# Sunday KMZ to 33 kV Network Plan

**Sprint Target:** Sunday, 16 August 2026  
**Status:** **Delivered & Production-Verified**  
**Authoritative Plan Reference:** [`docs/whats-next.md`](../../docs/whats-next.md)

---

> [!success] Milestone Delivery Status (as of 2026-08-16)
> The end-to-end KMZ-to-33kV optimization pipeline is **fully delivered and operational** across all three tiers:
> 1. **Python GIS & Optimization Microservice**: 79 source files, ~489 automated tests. Features: Multi-layer avoidance rasterization (road/HT line/watercourse crossings and restricted areas), capacity-constrained K-Means/MILP grouping, per-feeder MST topology, cost-surface A* routing with supercover shortcutting, Pandapower AC Newton-Raphson load-flow validation, network-level pole placement with endpoint deduplication (`pnc_pole`), canonical engineering metrics (PY-026), 4-group unified benefit scoring (PY-027), 25-year Decimal lifecycle costing (PY-028/029), and backwards-compatible V1 + explicit V2 REST endpoints.
> 2. **Java Backend Microservice**: Spring Boot 3.3.2 / Java 21, Flyway migrations V1–V13, 112 source files, 209 tests. Features: JWT auth, async executor, SSE progress streaming, PDFBox/CSV reporting, audit logging, admin user management, and `ScenarioProfile` bias integration.
> 3. **Modern Frontend (`web-map-next`)**: React 18, TypeScript, Vite, Leaflet with `preferCanvas`, TanStack Query v5, Zustand v4, Radix UI, Tailwind CSS v3, 65 source files, 26 Vitest tests. Features: Multi-layer GIS toggles (turbines, substations, feeder routes, 4 pole classes, parcels, restricted zones), interactive BoM strip & pane with AC losses and corridor intersection compensation, "Why this route?" decision summary card, and live SSE progress tracking.

---

## Historical Goal & Scope

A user uploads and reviews a KMZ/KML containing WTG coordinates and one substation. SURGE then uses confirmed project roads, parcels, and restricted areas to generate several radial collector candidates, electrically screens them at 33 kV, recommends the best eligible candidate, places preliminary pole types, and displays the result on the web map.

“Best” means highest ranked among SURGE's bounded, electrically valid candidates under the disclosed constraints and weights. It is not a global or construction-ready optimum.

---

## Input Invariants & Avoidance Layer Rules

A point-only KMZ is insufficient for road/land avoidance. Roads and land zones must exist in the same KMZ or a companion reviewed import.

- **Restricted/No-Go Land**: Hard exclusion rasterized with infinite traversal cost.
- **Roads / HT Lines / Watercourses**: Buffered soft crossing penalties encouraging perpendicular crossings.
- **Cadastral Parcels**: Soft land-impact resistance penalty.
- **Explicitly Confirmed Obstacles**: Hard exclusion.

---

## Delivered Architecture Checklist

### 1. Python Optimization Microservice (P0 - Delivered)
- [x] Hard exclusions and soft road/parcel penalties cleanly separated on raster cost surfaces.
- [x] Hard-buffer endpoint validation prevents placing turbines/substations in exclusionary zones.
- [x] Additive V1 and explicit V2 API contracts operating at nominal 33 kV.
- [x] SURGE-PY-023 merges shared pole endpoints into deterministic `junction` physical structures.
- [x] SURGE-PY-024 / PY-025 attaches deduplicated physical pole infrastructure (`pnc_pole`) to GeoJSON presentation.
- [x] SURGE-PY-026 extracts canonical candidate engineering metrics across spatial, infrastructure, and electrical domains.
- [x] SURGE-PY-027 unifies spatial and electrical metrics into a 4-group normalized benefit policy with 12-decimal precision tie-breaking.
- [x] SURGE-PY-028 computes 25-year discounted lifecycle costs (CAPEX + OPEX NPV) using `Decimal` arithmetic.
- [x] ~489 automated tests passing with Ruff, black, and strict MyPy typing.

### 2. Java Backend Integration (P0 - Delivered)
- [x] Loads project reference lines, cadastral parcels, and restricted areas from PostGIS on job execution.
- [x] Serializes constraint layers and forwards them to Python's optimization endpoints.
- [x] Validates substation selection and enforces configured 33 kV operating parameters.
- [x] Persists rich optimization results and routes without discarding pole features.
- [x] Exposes asynchronous job status with real-time Server-Sent Events (SSE).

### 3. Frontend `web-map-next` (P0 - Delivered)
- [x] Renders multi-layer wind farm features: WTGs, substations, feeder routes colored by feeder, parcels, restricted zones, and 4 pole classes (`terminal`, `angle`, `intermediate`, `junction`).
- [x] Displays preliminary pole popups and comprehensive recommendation rationale ("Why this route?").
- [x] Provides interactive Bill of Materials (BoM) pane with electrical loss calculations and corridor intersection compensation.
- [x] Handles running, failed, and completed job states with live SSE updates and robust error boundaries.

---

## Demonstration Workflow

1. **Upload & Review**: Upload wind farm KMZ; review parsed turbines, substation, parcels, and restricted areas in the interactive map preview.
2. **Configure Optimization**: Select candidate count (e.g., 3), cable specifications, and policy weights (Physical, Spatial, Infrastructure, Electrical, Cost).
3. **Execute Async Job**: Track real-time progress via SSE stream (grouping $\to$ routing $\to$ load flow $\to$ metrics $\to$ scoring $\to$ pole placement).
4. **Inspect Recommendations**: View recommended radial collector network; inspect plain-language trade-off reasons; examine voltage profiles and line loadings.
5. **Inspect Infrastructure**: Zoom into route corridors to inspect individual transmission pole classifications (`terminal`, `angle`, `intermediate`, `junction`).
6. **Export Artifacts**: Download RFC 7946 GeoJSON, BoM CSV reports, and PDF engineering decision summaries.

---

## Related Notes

- [[Overview & Layout]]
- [[Surge MVP Ticket Plan]]
- [[presentation-boundary|Python Presentation Boundary]]
- [[Candidate PNC Scenario Generation]]
- [[AC Load Flow Validation]]
- [[Multi-Objective Candidate Scoring]]
- [[Canonical Candidate Engineering Metrics]]
- [[Geospatial Integrity & CRS]]
