# Surge MVP Ticket Plan

**Canonical as of:** 2026-08-16  
**Status:** All core MVP & post-MVP Python tickets (SURGE-PY-014 through SURGE-PY-028) are **Complete**.  
**Test Suite:** ~489 passing automated tests in `optimisation-python/tests/`.

This document is the authoritative engineering record of the Python GIS & Optimization Service ticket sequence, module responsibilities, frozen interfaces, and architectural boundaries.

---

## Canonical Ticket Sequence & Status

| Ticket | Ticket Name | Status | Module & Primary Responsibility |
| --- | --- | --- | --- |
| **SURGE-PY-014** | Automatic PNC Network Assembly | **Complete** | `app/pnc/` — Assembles validated `ProjectPNCNetwork` instances from routing, topology, and grouping stages with deterministic segment and feeder IDs. |
| **SURGE-PY-015** | Pandapower Electrical Network + AC Load-Flow | **Complete** | `app/electrical/load_flow/` — Evaluates AC Newton-Raphson load flow for a PNC without mutation, trapping non-convergence as structured violations. |
| **SURGE-PY-016** | Map-Ready PNC Result Packaging + GeoJSON | **Complete** | `app/presentation/` — Reconciles physical network and electrical results into map-ready WGS84 GeoJSON and summary models. |
| **SURGE-PY-017** | Candidate PNC Scenario Generation | **Complete** | `app/optimisation/scenarios.py` — Generates 1–5 distinct, structurally valid PNC candidates using a 5-personality parameter schedule and pre-routing fingerprinting. |
| **SURGE-PY-018** | Multi-Objective Scoring + Recommendation | **Complete** | `app/optimisation/scoring.py` — Scores electrically evaluated candidates via cohort min-max normalization and provides explainable recommendation rationales. |
| **SURGE-PY-019** | End-to-End Optimisation Orchestrator | **Complete** | `app/optimisation/orchestrator.py` — Unifies preprocessing, candidate generation, load flow, scoring, and presentation behind `optimise_project()`. |
| **SURGE-PY-020** | MVP Demo API + End-to-End Validation | **Complete** | `app/api/v1/` & `app/api/v2/` — Implements backward-compatible V1 endpoint and explicit engineering V2 endpoint, verified against golden demo fixtures. |
| **SURGE-PY-021** | V1 Constraint Regression Coverage | **Complete** | `tests/api/test_optimise_v1.py` — Verifies hard exclusions, soft penalty rasters, and legacy constraint compatibility. |
| **SURGE-PY-022** | Constraint Fixture Provenance Labeling | **Complete** | `tests/fixtures/` — Formally documents hand-authored constraint fixtures and cross-team KMZ-to-JSON verification procedures. |
| **SURGE-PY-023** | Network-Level Pole Endpoint Deduplication | **Complete** | `app/algorithms/pole_placement.py` — Merges coincident shared topology endpoints into deterministic `junction` pole structures while preserving route-local span traceability. |
| **SURGE-PY-024** | Pole Placement Integration into Orchestrator | **Complete** | `app/optimisation/orchestrator.py` — Executes pole placement and endpoint deduplication for the winning candidate (or cohort), attaching `pole_network` to workflow results. |
| **SURGE-PY-025** | Pole GeoJSON + API Presentation | **Complete** | `app/presentation/geojson.py` — Serializes deduplicated physical poles as stable WGS84 `pnc_pole` Point features with connection and classification telemetry. |
| **SURGE-PY-026** | Canonical Candidate Engineering Metrics | **Complete** | `app/optimisation/engineering_metrics.py` — Extracts unified physical, spatial, infrastructure, and electrical metrics (`CandidateEngineeringMetrics`) for all evaluated candidates. |
| **SURGE-PY-027** | Unified Candidate Scoring Policy | **Complete** | `app/optimisation/scoring.py` — Unifies spatial, infrastructure, and electrical metrics into a 4-group normalized benefit policy with 12-decimal precision tie-breaking. |
| **SURGE-PY-028** | Lifecycle Cost Model (CAPEX + OPEX) | **Complete** | `app/costing/` — Implements 25-year discounted cash-flow NPV lifecycle cost model using Python `Decimal` arithmetic for conductors, poles, land ROW, and annual losses. |

---

## Detailed Ticket Specifications & Boundaries

### SURGE-PY-014: Automatic PNC Network Assembly
- **Module:** `app/pnc/` (`assembly.py`, `models.py`, `errors.py`, `geojson.py`)
- **Input:** Projected `ProjectSpatialData`, `feeder_capacity_mw`, `CostSurface`.
- **Output:** Validated `ProjectPNCNetwork` containing typed `PNCFeeder` and `PNCSegment` records.
- **Rules:**
  - Zero algorithm logic duplicated; coordinates and calls `wtg_grouping.py`, `route_graph.py`, `topology.py`, `physical_routing.py`, and `route_refinement.py`.
  - Deterministic ID formatting: `FDR-001`, `SEG-FDR001-0001`.
  - Strict validation against structural failures: raises `PNCAssemblyError` with specific codes (e.g., `FEEDER_WITHOUT_SUBSTATION_CONNECTION`, `UNROUTED_TOPOLOGY_EDGE`, `ORPHAN_WTG`, `DUPLICATE_WTG_ASSIGNMENT`).
  - See [[PNC Network Assembly]].

### SURGE-PY-015: Pandapower AC Load Flow Validation
- **Module:** `app/electrical/load_flow/` (`analysis.py`, `builder.py`, `config.py`, `models.py`)
- **Input:** `ProjectPNCNetwork`, `LoadFlowConfig` (cable library, voltage thresholds, nominal 33 kV), `WTGOperatingPoint` map.
- **Output:** `LoadFlowNetworkResult` containing per-bus, per-segment, per-feeder, and network-level power flow metrics.
- **Rules:**
  - Positive generator injection sign convention: $P > 0$ denotes generation into the grid.
  - Deterministic `pandapowerNet` builder with sorted node/segment indices and bidirectional index maps (`node_to_bus`, `segment_to_line`).
  - Graceful non-convergence: solver divergence does not raise Python exceptions; it returns `converged = False`, `is_valid = False`, and `violations = [LoadFlowViolation(code="LOAD_FLOW_NOT_CONVERGED")]`.
  - See [[AC Load Flow Validation]].

### SURGE-PY-016: Map-Ready Result Packaging & Presentation
- **Module:** `app/presentation/` (`result_builder.py`, `geojson.py`, `models.py`, `exceptions.py`)
- **Input:** `ProjectPNCNetwork`, `LoadFlowNetworkResult`.
- **Output:** `ProjectOptimizationResult` with enriched RFC 7946 WGS84 GeoJSON `FeatureCollection`.
- **Rules:**
  - Reconciles physical network and electrical results; raises `PresentationDataMismatchError` on mismatched topology or non-finite numbers.
  - Generates stable feature IDs: `substation-{id}`, `wtg-{id}`, `segment-{id}`, `pole-{id}`.
  - Feature coordinates strictly transformed to WGS84 (EPSG:4326) with computed collection bounding box `[west, south, east, north]`.
  - Nullable electrical properties and boolean violation flags ensure consistent frontend map rendering even when load flow fails to converge.
  - See [[presentation-boundary|Python Presentation Boundary]].

### SURGE-PY-017: Candidate PNC Scenario Generation
- **Module:** `app/optimisation/scenarios.py` & `scenario_models.py`
- **Input:** `ProjectSpatialData`, `feeder_capacity_mw`, `CostSurface`, `ScenarioGenerationConfig`.
- **Output:** `ScenarioGenerationResult` with 1–5 distinct, valid `PNCScenario` instances.
- **Rules:**
  - Iterates through 5 fixed parameter personalities:
    1. `PS-001 (baseline)`: seed 42, MINIMIZE_DISTANCE, default weights.
    2. `PS-002 (alternative_grouping)`: seed 17, MINIMIZE_DISTANCE, default weights.
    3. `PS-003 (balanced_feeders)`: seed 42, BALANCE_WTG_COUNT MILP objective.
    4. `PS-004 (long_edge_penalty)`: seed 42, distance weighting $\alpha = 2.0$, $w' = w \cdot (1 + \alpha \cdot w / w_{\max})$.
    5. `PS-005 (alternative_grouping_balanced)`: seed 7, BALANCE_WTG_COUNT MILP objective.
  - Computes topology fingerprint `v1:<sha256(canonical_json)>` prior to A* routing; identical topologies are skipped with `AttemptOutcome.DUPLICATE_TOPOLOGY`.
  - See [[Candidate PNC Scenario Generation]].

### SURGE-PY-018: Multi-Objective Candidate Scoring & Recommendation
- **Module:** `app/optimisation/scoring.py` & `scoring_models.py`
- **Input:** Cohort of `ElectricallyEvaluatedScenario` records, scoring configuration/weights.
- **Output:** Ranked cohort with selected winning candidate, normalized metric scores, and explainable reasons (`BEST_METRIC`, `GROUP_STRENGTH`, `TRADE_OFF_ACCEPTED`).
- **Rules:**
  - Evaluates cohort min-max normalization over feasible candidates only.
  - Non-converged or electrically invalid candidates are disqualified and cannot be recommended.
  - Quantizes final scores to 12 decimal places with deterministic cascading tie-breakers.
  - See [[Multi-Objective Candidate Scoring]].

### SURGE-PY-019: End-to-End Optimisation Orchestrator
- **Module:** `app/optimisation/orchestrator.py` & `workflow_models.py`
- **Function:** `optimise_project(project_input, config)`
- **Workflow Pipeline:**
  ```text
  ProjectInput validation
      → CRS projection & CostSurface preparation
      → Multi-candidate generation (PY-017)
      → Pandapower AC load flow execution (PY-015)
      → Canonical engineering metrics extraction (PY-026)
      → Lifecycle costing (PY-028, optional)
      → Multi-objective scoring & winner selection (PY-027)
      → Pole placement & deduplication on winner (PY-023 / PY-024)
      → Result presentation packaging (PY-016 / PY-025)
      → OptimisationWorkflowResult
  ```
- **Error Isolation:** Candidate-local electrical, extraction, or presentation errors are isolated with explicit diagnostic codes without terminating the global workflow.

### SURGE-PY-020: MVP Demo API & Golden Fixture Validation
- **Module:** `app/api/v1/` and `app/api/v2/`
- **Endpoints:**
  - `POST /api/v1/optimise`: Backward-compatible DTO interface. Returns legacy fields (`feeder_routes_geojson`, `metrics`, `status`) populated from the recommended candidate, alongside additive multi-scenario data.
  - `POST /api/v2/optimise`: Explicit engineering interface requiring conductor libraries and operating parameters, returning complete candidate comparisons.
- **Golden Fixtures:** `tests/fixtures/mvp_demo_project_v2.json` and `constraint_demo_project_v2.json` verify deterministic multi-candidate output and WGS84 GeoJSON validity.

### SURGE-PY-021: V1 Constraint Regression Coverage
- **Module:** `tests/api/test_optimise_v1.py`
- **Scope:** Enforces V1 API behavior when supplied with `avoidance_geojson`: verifies hard exclusion geometry clipping, soft penalty resistance, endpoint proximity rejections, and byte-for-byte reproducibility.

### SURGE-PY-022: Constraint Fixture Provenance Labeling
- **Module:** `tests/fixtures/README.md`
- **Scope:** Formally documents test fixture provenance, separating hand-crafted JSON contracts from raw KMZ parsing pipelines and recording cross-stack verification protocols.

### SURGE-PY-023: Network-Level Pole Endpoint Deduplication
- **Module:** `app/algorithms/pole_placement.py` (`deduplicate_pole_endpoints()`)
- **Scope:** Post-processing pass over route-local pole placements. Merges coincident terminal poles at shared topology vertices into single physical `junction` poles within a pairwise distance tolerance ($< 0.1\text{ m}$), preserving route-local span connectivity and feeder references.

### SURGE-PY-024: Pole Placement Integration into Orchestrator
- **Module:** `app/optimisation/orchestrator.py`
- **Scope:** Integrates pole placement into `optimise_project()`. Executes placement and PY-023 deduplication on the recommended candidate (or caches across candidates), attaching the canonical `CollectorPoleResult` to `OptimisationWorkflowResult.pole_network`.

### SURGE-PY-025: Pole GeoJSON & Presentation Integration
- **Module:** `app/presentation/geojson.py` & `result_builder.py`
- **Scope:** Extends GeoJSON presentation to serialize deduplicated physical poles as `pnc_pole` Point features with properties: `pole_id`, `pole_type` (`terminal`, `angle`, `intermediate`, `junction`), `connected_feeder_ids`, `connected_route_ids`, `connected_node_ids`, and coordinate elevation.

### SURGE-PY-026: Canonical Candidate Engineering Metrics
- **Module:** `app/optimisation/engineering_metrics.py` & `engineering_metric_models.py`
- **Scope:** Standardizes metric extraction across spatial, infrastructure, and electrical domains into `CandidateEngineeringMetrics` (route length, traversal cost, parcel count, road crossings, soft corridor overlap, environmental overlap, physical poles, active losses, cable loading, voltage operating margin).
- **Availability:** All-or-nothing model with structured `extraction_failures` (e.g., `POLE_CONFIG_MISSING`).
- **See:** [[Canonical Candidate Engineering Metrics]].

### SURGE-PY-027: Unified Candidate Scoring Policy
- **Module:** `app/optimisation/scoring.py` & `scoring_models.py`
- **Scope:** Replaces legacy spatial-only scoring with a unified 4-group multi-objective benefit model (Physical, Spatial, Infrastructure, Electrical) using PY-026 canonical metrics, cohort min-max normalization, and 12-decimal quantized ranking.
- **See:** [[Multi-Objective Candidate Scoring]].

### SURGE-PY-028: Lifecycle Cost Model (CAPEX + OPEX)
- **Module:** `app/costing/` (`lifecycle.py`, `models.py`, `catalogue.py`, `failures.py`)
- **Scope:** Computes 25-year discounted cash-flow NPV lifecycle cost using Python `Decimal` arithmetic:
  - **CAPEX:** Conductor cable supply/installation, overhead poles by type, fixed & variable land acquisition/easements, road crossing permits.
  - **OPEX:** Annual active electrical energy losses discounted at $(1 + r)^{-y}$, plus annual infrastructure maintenance percentages.
  - **Integration (PY-029):** Integrates economic benefit into unified cohort scoring.

---

## Related Notes

- [[Overview & Layout]]
- [[Candidate PNC Scenario Generation]]
- [[AC Load Flow Validation]]
- [[Canonical Candidate Engineering Metrics]]
- [[Multi-Objective Candidate Scoring]]
- [[PNC Network Assembly]]
- [[presentation-boundary|Python Presentation Boundary]]
- [[Geospatial Integrity & CRS]]
- [[Route Scoring Architecture]]
