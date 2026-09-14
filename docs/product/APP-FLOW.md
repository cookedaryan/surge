# Application Flow Document (APP-FLOW)
## SURGE — Smart Utility Routing and Grid Evacuation

**Status:** Living document — MVP phase
**Companion documents:** [PRD.md](PRD.md) (what/why), [TRD.md](../architecture/TRD.md) (how)
**Last aligned with repo state:** 2026-08-08

---

## 1. Purpose

This document describes the end-to-end user journey through the SURGE web application — screen by screen, action by action — and how each screen maps to backend services. It is the reference for frontend implementation and for QA/acceptance walkthroughs.

---

## 2. High-Level Journey

```text
 Create Project
      │
      ▼
 Upload GIS Layers
      │
      ▼
 Configure Optimisation Scenario
      │
      ▼
 Generate Network  ──▶ (Java → Python /api/v1/optimise)
      │
      ▼
 Review Network Results (map)
      │
      ▼
 Compare Scenarios
      │
      ▼
 Export Reports
```

Each stage corresponds to a screen in the web-map frontend, backed by REST calls to the Java Spring Boot API, which in turn calls the Python optimisation service for the compute-heavy steps.

---

## 3. Screen-by-Screen Flow

### Screen 1 — Project Setup
**Goal:** Establish the project's identity and inputs.

**User actions:**
- Enter project name.
- Draw or upload the study-area boundary.
- Upload WTG locations (each with `id`, coordinates, `capacity_mw`).
- Select or upload the substation location.
- Enter electrical parameters: feeder capacity (MW), max voltage drop (%), ROW width (m).

**System behavior:**
- Java persists the project, WTGs, and substation to PostGIS.
- Basic geometry validation occurs on upload (valid Point geometry, required properties present).

**Exit condition:** Project exists with at least one substation and one or more WTGs → user proceeds to Screen 2.

---

### Screen 2 — GIS Layers
**Goal:** Supply the environmental and land context the optimisation needs.

**User actions:**
- Drag-and-drop or upload layers: roads, forest, water, cadastral parcels, elevation (DEM), restricted areas, land compensation rates.

**System behavior:**
- Each layer is validated (geometry validity, CRS handling) before acceptance.
- Layers are stored as GIS-layer metadata + spatial data in PostGIS, associated with the project.
- Layers not yet consumed by the optimisation pipeline (e.g., DEM-based terrain cost) are accepted and stored today, even though the Python engine does not yet rasterize/consume all of them — this is a known, documented implementation gap (see TRD §5.1, §11).

**Exit condition:** Required layers for the chosen scenario are present → user proceeds to Screen 3. (Layers can be revisited later.)

---

### Screen 3 — Optimisation Settings
**Goal:** Configure how alternatives should be generated and scored.

**User actions:**
- Select a scenario: **Minimum Cost**, **Minimum Land Impact**, **Minimum Environmental Impact**, or **Balanced**.
- Adjust cost weights (for Balanced, or as an advanced override).
- Set feeder capacity, ROW width, span limits, max voltage drop, and candidate count.

**System behavior:**
- Java packages the project's WTGs, substation, GIS context, scenario, and electrical parameters into an optimisation request.
- Java calls `POST /api/v1/optimise` on the Python service synchronously (per current implementation — async job polling is planned but not yet built).

**Exit condition:** User submits → triggers Screen 4 (with a loading/progress state while the Python service computes).

---

### Screen 4 — Network Results (Map)
**Goal:** Visualize the generated network for the current scenario.

**Displayed elements:**
- WTG clusters (feeder groupings)
- Feeder routes (currently: preliminary straight-edge topology from the MST step; full terrain-aware corridors are planned)
- Junctions (planned)
- Poles (planned)
- ROW corridors (planned)
- Impacted parcels (planned)

**System behavior today:**
- The map renders whatever the Python response contains: feeder count, aggregate preliminary length, and WGS84 LineString features per selected edge.
- Because pole placement, ROW generation, and parcel intersection are not yet implemented in the Python engine, those layers may show placeholder/empty states in the current build — the frontend already includes demo-data fallbacks for exactly this situation.

**User actions:**
- Pan/zoom the map, toggle layers, inspect individual feeders/edges.
- Return to Screen 3 to adjust configuration and regenerate, or proceed to Screen 5 to compare against other scenarios.

---

### Screen 5 — Scenario Comparison
**Goal:** Let the user weigh alternatives side by side.

**Displayed table (per scenario/route alternative):**

| Metric | Route A | Route B | Route C |
|---|---:|---:|---:|
| Length | | | |
| Estimated cost | | | |
| Pole count | | | |
| Parcel count | | | |
| ROW area | | | |
| Forest impact | | | |
| Voltage drop | | | |
| Power loss | | | |
| Overall score | | | |

**System behavior:**
- Each column is one generated alternative; each row is a contributing metric feeding that alternative's overall score (explainability requirement from the PRD).
- Until cost, electrical, and land-impact modules are implemented, several rows will be unavailable/placeholder — this table's shape is the contract the backend is being built toward, not a claim that all cells are populated today.

**User actions:**
- Select a "winning" alternative to carry forward to export.
- Re-run with a different scenario for comparison.

---

### Screen 6 — Reports
**Goal:** Get results out of SURGE for downstream use (regulatory, land, engineering handoff).

**Available exports:**
- Route GeoJSON
- Pole schedule CSV
- Parcel-impact CSV
- Route comparison PDF
- Electrical-results CSV

**System behavior:**
- Java aggregates stored results (BOM/CSV aggregation is already implemented) and generates the requested export format.
- Exports for modules not yet implemented in Python (poles, parcels, electrical results) will be incomplete until those modules land — this should be surfaced honestly in the UI (e.g., "preliminary" labeling) rather than fabricated.

**Exit condition:** User downloads one or more reports — end of primary flow. User may return to Screen 1 to start a new project or Screen 3 to iterate.

---

## 4. Cross-Cutting Flow Notes

### 4.1 Error / Fallback Behavior
- The current web-map frontend uses **demo fallbacks** when certain API calls fail. This is acceptable for early development but must be clearly distinguished from real results in the UI before any user-facing release (label demo data explicitly).

### 4.2 Synchronous vs. Asynchronous Optimisation
- Today: Screen 3 → Screen 4 is a synchronous call chain (Java blocks on Python's response).
- Planned: asynchronous job submission with polling/status, since full-pipeline runs (routing + poles + ROW + electrical + ranking) will take longer than a simple MST call. This will change Screen 4's loading UX from a blocking spinner to a job-status view — flag this as a near-term UX change, not a current implemented behavior.

### 4.3 Data Provenance Through the Flow
```text
Browser (WGS84 GeoJSON)
   → Java (validates, persists in PostGIS, still WGS84)
   → Python (projects to UTM for computation)
   → Python (computes, returns WGS84 GeoJSON)
   → Java (persists results, resolves feeder identity — see TRD §6.3 known gap)
   → Browser (renders on Leaflet map)
```

### 4.4 Explainability Touchpoint
Every screen from 4 onward must be able to answer "why this result?" — this is a product requirement (PRD §8), not just a UI nicety. Screen 5's comparison table is the primary explainability surface; it should always show contributing metrics alongside any aggregate score, and should never present an ML-derived score without labeling it experimental if the deterministic score isn't also shown.

---

## 5. Flow-to-Component Traceability

| Screen | Primary Frontend Concern | Primary Java Responsibility | Primary Python Responsibility |
|---|---|---|---|
| 1. Project Setup | Forms, boundary drawing | Project/WTG/Substation persistence | — |
| 2. GIS Layers | Drag-and-drop upload | GIS-layer metadata + storage | GIS validation (on submit) |
| 3. Optimisation Settings | Scenario/weight controls | Package + dispatch optimisation request | Request validation |
| 4. Network Results | Map rendering, layer toggles | Store returned metrics/routes | Grouping, topology, (planned: routing, poles, ROW) |
| 5. Scenario Comparison | Comparison table | Aggregate metrics across runs | Scoring/ranking (planned), metric output |
| 6. Reports | Export triggers | Report/export generation (BOM/CSV) | Supplies underlying metrics |

---

## 6. Open UX Items Tied to Known Technical Gaps

- Screen 4 needs a visible "preliminary topology only" indicator until terrain-aware routing (A*) replaces the Euclidean MST.
- Screen 5's table needs graceful empty/placeholder states for cost, land, and electrical columns until those backend modules exist — not fabricated numbers.
- Screen 6 exports should carry the same "preliminary/planned" labeling as the screens they're derived from, so downstream consumers (land, regulatory) never mistake MVP output for final engineering data.
