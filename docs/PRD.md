# Product Requirements Document (PRD)
## SURGE — Smart Utility Routing and Grid Evacuation

**Status:** Living document — MVP phase
**Owners:** Java/Backend Developer, Python/GIS/ML Developer
**Last aligned with repo state:** 2026-08-08

---

## 1. Purpose

SURGE is an enterprise-grade platform that helps engineers design renewable-energy **collector and evacuation networks** — the electrical infrastructure that carries power from Wind Turbine Generators (WTGs) to a substation. The product's job is to move design work beyond "draw the shortest line between turbines and a substation" and instead produce complete, engineering-grade, **explainable** alternatives that account for cost, land impact, environmental impact, and electrical performance simultaneously.

This document defines what SURGE must do for its users, why, and how success is measured. It does not prescribe implementation — see the TRD for that.

---

## 2. Problem Statement

Designing a 33kV (or similar) collector network today is a manual, engineering-heavy process:

- Engineers must manually group turbines into feeders within capacity limits.
- Routes must respect terrain, forests, restricted areas, roads, and rivers.
- Every route implies a Right-of-Way (ROW) corridor that intersects cadastral land parcels, each with a compensation cost.
- Pole placement and spans must be electrically and structurally valid.
- Voltage drop, conductor loading, and power loss must stay within limits.
- Multiple competing objectives (cost, land, environment, electrical performance) must be weighed against each other, and the reasoning behind a chosen route must be auditable.

Doing this by hand is slow, inconsistent across engineers, and hard to justify to regulators, landowners, or internal reviewers. SURGE automates this pipeline while preserving explainability at every step.

---

## 3. Product Vision

SURGE combines GIS analysis, electrical validation, mathematical optimization, and explainable decision support into one platform. Given turbine and substation locations plus environmental/land data, it should output multiple complete, comparable network designs — not just geometry, but pole placement, land impact, electrical validation, and a transparent score for each alternative.

**Target lifecycle coverage (full product, not MVP):**
WTG grouping → radial feeder topology → geographic routing → pole placement → variable spans → electrical constraints → land/ROW impact → lifecycle cost → scenario comparison.

---

## 4. Users and Personas

| Persona | Role | Needs from SURGE |
|---|---|---|
| **Design Engineer** | Plans the collector network for a wind farm project | Fast generation of feasible route alternatives; confidence that constraints (electrical, terrain, land) are respected |
| **Project/Land Manager** | Manages land acquisition and compensation | Clear parcel-impact and compensation estimates per alternative |
| **Reviewing Engineer / QA** | Approves a chosen design | Auditable, explainable score breakdowns per alternative; evidence that hard constraints were not violated |
| **Platform Developer** (internal) | Builds and extends SURGE | Clear contracts between Java, Python, and frontend; documented implementation boundary (this repo's docs already track this) |

---

## 5. Goals and Non-Goals

### Goals (MVP)
1. Ingest WTGs, one substation, and supporting GIS layers for a single project area.
2. Automatically group WTGs into feeders and generate a radial collector topology.
3. Generate at least three candidate routed alternatives per project.
4. Place poles with variable spans and preliminary pole-type recommendations.
5. Generate ROW corridor polygons and compute affected parcels + compensation.
6. Run preliminary electrical validation (voltage drop, conductor loading, power loss).
7. Support four comparable optimization scenarios: Minimum Cost, Minimum Land Impact, Minimum Environmental Impact, Balanced.
8. Present every score with its contributing metrics (explainability), not a black-box number.
9. Allow export of results (GeoJSON routes, pole schedule CSV, parcel-impact CSV, comparison report).

### Non-Goals (explicitly deferred post-MVP)
- Structural/foundation-level pole design.
- Statutory/regulatory approval workflows.
- Production-scale, multi-project, multi-tenant optimization.
- Advanced scenarios: Minimum Pole Count, Maximum Span, Future Expansion.
- Full authentication/authorization hardening, async job processing at scale, Kubernetes deployment.

---

## 6. Core Concepts (Glossary)

- **Collector network** — the electrical network carrying generation from WTGs toward a substation.
- **Feeder** — a branch of the network with an electrical capacity limit.
- **Topology** — which assets connect, independent of physical corridor.
- **Route** — the geographic LineString realizing a topology connection.
- **ROW corridor** — the land strip required around a route for construction, operation, and clearance.
- **Multi-objective optimization** — comparing alternatives across cost, land, environment, and electrical performance.
- **Explainability** — preserving inputs, constraints, raw metrics, weights, algorithm choice, and rejection reasons so any result can be audited.

---

## 7. Functional Requirements

### 7.1 Project Setup
- User can create a project with a name and study-area boundary.
- User can upload WTG locations (with capacity) and select/upload a substation location.
- User can specify electrical parameters (feeder capacity, max voltage drop %, ROW width).

### 7.2 GIS Layer Management
- User can upload supporting layers: roads, forest, water, cadastral parcels, elevation (DEM), restricted areas, land compensation rates.
- System validates uploaded GIS data (valid geometry, correct CRS handling) before use.

### 7.3 Optimization Configuration
- User selects a scenario (Minimum Cost / Minimum Land Impact / Minimum Environmental Impact / Balanced) or sets custom cost weights.
- User can configure feeder capacity, ROW width, span limits, max voltage drop, and candidate count.

### 7.4 Network Generation
- System groups WTGs into capacity-constrained feeders.
- System generates a radial collector topology per feeder (minimum spanning tree today; terrain/exclusion-aware routing planned).
- System identifies preliminary junction locations.
- System places poles with non-uniform (variable) spans and assigns preliminary pole types.

### 7.5 Land and Environmental Impact
- System generates ROW corridor polygons around each candidate route.
- System computes intersecting cadastral parcels and estimated compensation cost.
- System reports forest/restricted-area intersection extent, road and river crossings.

### 7.6 Electrical Validation
- System runs load-flow-style validation (voltage drop %, conductor loading, power loss).
- System rejects electrically invalid candidates rather than presenting them as viable.

### 7.7 Scenario Comparison and Ranking
- System produces at least three alternatives and scores each against the selected scenario's weighting.
- System (baseline) uses deterministic scoring; an experimental ML ranking model may supplement it once sufficient labeled data exists — ML results are always labeled as experimental unless promoted.
- Every score is shown with the metrics that produced it (length, cost, pole count, parcel count, ROW area, forest impact, voltage drop, power loss).

### 7.8 Reporting and Export
- User can export: route GeoJSON, pole schedule CSV, parcel-impact CSV, route comparison PDF/report, electrical-results CSV.

---

## 8. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Explainability** | Every generated score must be traceable to its inputs, constraints, weights, and algorithm — no opaque results. |
| **Correctness / Safety** | Hard engineering constraints (feeder capacity, electrical limits, hard exclusions) must never be silently violated; invalid candidates must be rejected, not hidden. |
| **Determinism** | Given identical inputs and configuration, topology/scoring output must be reproducible (documented, tested behavior — e.g., sorted edge selection). |
| **Auditability** | Assumptions, decisions, and known limitations must be documented alongside results (mirrors the project's Obsidian/requirement-traceability practice). |
| **Usability** | Map-based visual workflow: upload → configure → generate → compare → export, without requiring GIS specialist tooling. |
| **Performance** | MVP targets a single controlled project area (8–12 WTGs) with interactive turnaround for a demo dataset; production-scale performance is out of MVP scope. |
| **Transparency of maturity** | The product must clearly label which capabilities are Implemented, Partial, or Planned at any point in time (this is an explicit documentation convention already in use). |

---

## 9. Success Metrics / Definition of Done (MVP)

The MVP is considered complete when:
- A user can create a project and load WTGs + a substation.
- GIS layers can be uploaded and validated.
- WTGs are automatically grouped and a feeder topology is generated.
- At least three route alternatives are produced, all respecting hard constraints.
- Poles, variable spans, ROW polygons, and affected parcels are calculated.
- Preliminary electrical validation runs and can reject invalid candidates.
- All four MVP scenarios can be compared side by side with visible contributing metrics.
- Results can be exported in the formats listed in §7.8.
- The full pipeline runs end-to-end via Docker Compose.
- Unit, integration, and golden-dataset tests pass.
- Known assumptions/limitations are documented.

The wider platform is ultimately evaluated on five axes: **optimisation quality, engineering feasibility, explainability, scalability, and integrated usability.** The MVP must provide measurable evidence for all five while clearly marking structural design, final foundations, statutory approval, and production-scale optimisation as post-MVP.

---

## 10. Current Status Snapshot (for traceability)

As of the last documented baseline:
- **Implemented:** GIS point validation, UTM projection, complete candidate graph construction, capacity-constrained WTG grouping (K-Means-assisted), per-feeder MST topology, a standalone uniform cost-surface abstraction, project/job persistence and BOM/CSV aggregation in Java, a working Leaflet-based map frontend with upload and live dashboard.
- **Not yet implemented:** Terrain/exclusion-aware routing (A*), converting topology edges into routed corridor geometry, pole placement, variable-span optimisation, ROW generation, parcel intersection and compensation, electrical load-flow validation, ML ranking, and full Java↔Python feeder-identity contract alignment.

This snapshot should be kept current as milestones close; see `Milestone 1 - Pending.md` and `Python Engine - Architecture.md` for the authoritative live status.
