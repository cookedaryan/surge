# Graph Report - obsidian-vault  (2026-09-13)

## Corpus Check
- 66 files · ~57,146 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 254 nodes · 554 edges · 27 communities (24 shown, 3 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.93)
- Semantic token usage: unavailable from the desktop subagent API; no paid API calls.

## Community Hubs (Navigation)
- Python Engine Engineering
- Network Optimisation Design
- Architecture Decision Records
- System Architecture
- FastAPI Endpoints
- ADR-002 Use PostGIS
- Product Vision and Scope
- Python Engine
- Testing Status
- Architecture Decision Records
- System Overview
- MVP Execution Planning
- MVP Execution Planning
- Product Vision and Scope
- Product Vision and Scope
- Functional Requirements
- Non Functional Requirements
- User Stories
- System Architecture
- 2026-08-07
- 2026-08-08
- 2026-08-15
- 2026-08-16-ark
- Product Vision and Scope
- Documentation Templates
- Documentation Templates
- Documentation Templates

## God Nodes (most connected - your core abstractions)
1. `SURGE Master Dashboard` - 35 edges
2. `Python Optimization Engine FastAPI Microservice` - 33 edges
3. `SURGE Vision and Core Capabilities` - 30 edges
4. `MVP Execution Plan Frontend and Java` - 29 edges
5. `Testing Strategy and Current Status` - 29 edges
6. `Functional Requirements` - 26 edges
7. `Spatial Physical Routing & Geometric Refinement` - 25 edges
8. `Project Goals and Strategic Objectives` - 24 edges
9. `Non Functional Requirements` - 24 edges
10. `System Architecture Overview` - 24 edges

## Surprising Connections (you probably didn't know these)
- `Vision lifecycle cost optimization` --semantically_similar_to--> `Implemented Decimal lifecycle costing`  [INFERRED] [semantically similar]
  01-vision/Vision.md → 05-optimization/Cost Model.md
- `Hard radial topology constraint` --semantically_similar_to--> `Implemented deterministic radial MST topology`  [INFERRED] [semantically similar]
  02-requirements/Constraints.md → 05-optimization/Per-Feeder MST Topology.md
- `SURGE Master Dashboard` --references--> `Project Goals and Strategic Objectives`  [EXTRACTED]
  00-dashboard/Dashboard.md → 01-vision/Goals.md
- `SURGE Master Dashboard` --references--> `Development Roadmap`  [EXTRACTED]
  00-dashboard/Dashboard.md → 01-vision/Roadmap.md
- `SURGE Master Dashboard` --references--> `Project Scope and Delivery Boundary`  [EXTRACTED]
  00-dashboard/Dashboard.md → 01-vision/Scope.md

## Hyperedges (group relationships)
- **Implemented feeder optimization pipeline** — 05_optimization_feeder_planning_end_to_end_pipeline, 05_optimization_per_feeder_mst_topology_deterministic_radial_mst, 04_architecture_python_engine_physical_routing_pipeline, 05_optimization_cost_model_decimal_lifecycle_costing [EXTRACTED 1.00]
- **Implemented SURGE vertical slice architecture** — 04_architecture_frontend_web_map_next, 04_architecture_backend_async_optimization_orchestration, 04_architecture_python_engine_physical_routing_pipeline, 04_architecture_database_wgs84_spatial_storage [EXTRACTED 1.00]

## Communities (27 total, 3 thin omitted)

### Community 0 - "Python Engine Engineering"
Cohesion: 0.08
Nodes (48): Deterministic load-flow grid builder, AC Load Flow Validation, Graceful load-flow non-convergence, Implemented Pandapower Newton-Raphson validation, Candidate attempt diagnostics, Implemented five-personality candidate schedule, Candidate PNC Scenario Generation, Pre-routing topology fingerprinting (+40 more)

### Community 1 - "Network Optimisation Design"
Cohesion: 0.07
Nodes (43): Hard radial topology constraint, Implemented route decision summary, Implemented deterministic engineering ground truth, Implemented candidate disqualification audit, Explainable Engineering Decisions and Audit Trail, Feeder Topology and Physical Network Planning, Implemented end to end feeder planning pipeline, Implemented radial topology invariant (+35 more)

### Community 2 - "Architecture Decision Records"
Cohesion: 0.09
Nodes (25): Vision lifecycle cost optimization, Implemented CAPEX and loss OPEX model, Implemented Decimal lifecycle costing, Lifecycle Cost Objective Model SURGE PY 028, Implemented partial cost failure reporting, Deterministic engineering safety boundary, ADR-003 ML Ranking document, Future ML candidate pre-ranking (deferred plan) (+17 more)

### Community 3 - "System Architecture"
Cohesion: 0.16
Nodes (16): Implemented administrator lockout protection, Authentication and Authorization Architecture, Implemented live JWT token validation, Implemented mandatory JWT secret, Implemented asynchronous optimization orchestration, Backend Architecture Java Spring Boot, Implemented Flyway schema evolution, Implemented SSE job progress streaming (+8 more)

### Community 4 - "FastAPI Endpoints"
Cohesion: 0.18
Nodes (12): FastAPI Microservice Specification, Request validation and HTTP error contract, Implemented V1 compatibility endpoint, Implemented V2 engineering endpoint, ADR-001: Use FastAPI for the Optimization Service, Accepted and implemented FastAPI computation boundary, FastAPI separation of concerns rationale, Versioned optimization REST contract (+4 more)

### Community 5 - "ADR-002 Use PostGIS"
Cohesion: 0.18
Nodes (12): ADR-002: Use PostGIS for Spatial Persistence, Accepted and implemented PostGIS authoritative store, PostGIS spatial indexing and SQL rationale, WGS84 public geometry and Flyway schema evolution, ADR-006 Spatial Models and Unified UTM document, Project mean-center UTM CRS selection, Unified local UTM projection (implemented), WGS84-to-UTM ingestion and egress boundary (+4 more)

### Community 6 - "Product Vision and Scope"
Cohesion: 0.20
Nodes (11): Deferred meshed routing and ML ranking, Delivered MVP scope boundary, Project Scope and Delivery Boundary, Implemented radial collector design scope, System and Engineering Constraints, Hard protected area exclusion, Hard voltage drop compliance limit, AC losses feed lifecycle cost (+3 more)

### Community 7 - "Python Engine"
Cohesion: 0.25
Nodes (8): Python Optimization Engine FastAPI Microservice, Implemented physical routing and pole pipeline, Implemented scoring and lifecycle costing, Implemented UTM spatial preprocessing, Journal 2026-08-16, Feeder color palette work (historical journal log), Per-pole reporting work (historical journal log), Vault overhaul (historical journal log)

### Community 8 - "Testing Status"
Cohesion: 0.25
Nodes (8): Testing Strategy and Current Status, Documented Java backend verification, Documented multi-tier CI matrix, Documented Python optimizer verification, Journal 2026-08-09, Five-phase routing pipeline (historical journal log), Gujarat Kutch benchmark data (historical journal log), Leaflet ingestion fixes (historical journal log)

### Community 9 - "Architecture Decision Records"
Cohesion: 0.25
Nodes (8): ADR-005 Python Service Architecture document, Frozen domain dataclasses, Transport-to-domain translation boundary, Two-model family architecture (implemented), Genetic Algorithms research note, Evolutionary topology optimization research, Kruskal radial MST topology (documented implementation), MILP WTG grouping (documented implementation)

### Community 10 - "System Overview"
Cohesion: 0.33
Nodes (6): Implemented asynchronous interservice data flow, Implemented containerized deployment stack, System Architecture Overview, Implemented microservice responsibility split, Requirement acceptance criteria (template), Requirement template

### Community 11 - "MVP Execution Planning"
Cohesion: 0.50
Nodes (4): Implemented four deterministic scenarios, SURGE Master Dashboard, Implemented end-to-end vertical slice MVP, Planned production security hardening backlog

### Community 12 - "MVP Execution Planning"
Cohesion: 0.50
Nodes (4): Completed phased backend and frontend workstreams, MVP Execution Plan Frontend and Java, Verified MVP release gate, Implemented versioned Java Python result contract

### Community 13 - "Product Vision and Scope"
Cohesion: 0.50
Nodes (4): Project Goals and Strategic Objectives, Goal complete engineering explainability, Goal lifecycle cost reduction, Goal rapid deterministic design turnaround

### Community 14 - "Product Vision and Scope"
Cohesion: 0.50
Nodes (4): Active production hardening phase, Completed phases one through three, Development Roadmap, Planned post MVP capabilities

### Community 15 - "Functional Requirements"
Cohesion: 0.50
Nodes (4): Functional Requirements, Implemented GIS asset ingestion requirement, Implemented optimization pipeline requirements, Implemented security and report export requirements

### Community 16 - "Non Functional Requirements"
Cohesion: 0.50
Nodes (4): Verified deterministic and transactional safety requirements, Non Functional Requirements, Verified performance and scalability targets, Verified security and usability quality requirements

### Community 17 - "User Stories"
Cohesion: 0.50
Nodes (4): Implemented administrator security workflow, User Stories and Acceptance Criteria, Implemented electrical engineer workflow, Implemented planning engineer workflow

### Community 18 - "System Architecture"
Cohesion: 0.50
Nodes (4): Database Architecture PostGIS and PostgreSQL, Implemented thirteen Flyway migrations, Implemented GiST spatial indexes, Implemented WGS84 spatial storage

### Community 19 - "2026-08-07"
Cohesion: 0.50
Nodes (4): Journal 2026-08-07, Geometry validation and repair (historical journal log), GIS pipeline implementation (historical journal log), WTG clustering next step (historical plan)

### Community 20 - "2026-08-08"
Cohesion: 0.50
Nodes (4): Journal 2026-08-08, Optimization orchestration (historical journal log), Security, SSE, and PDF next steps (historical plan), Spatial migration and JPA entities (historical journal log)

### Community 21 - "2026-08-15"
Cohesion: 0.50
Nodes (4): After-commit SSE visibility fix (historical journal log), Journal 2026-08-15, Scenario profiles (historical journal log), Security hardening (historical journal log)

### Community 22 - "2026-08-16-ark"
Cohesion: 0.50
Nodes (4): Candidate search reliability work (historical journal log), Journal 2026-08-16 ARK, Land context integration (historical journal log), Pole micro-siting work (historical journal log)

### Community 23 - "Product Vision and Scope"
Cohesion: 0.67
Nodes (3): Vision cost surface route optimization, SURGE Vision and Core Capabilities, Vision explainable deterministic scenarios

## Knowledge Gaps
- **135 isolated node(s):** `Implemented end-to-end vertical slice MVP`, `Implemented four deterministic scenarios`, `Verified MVP release gate`, `Implemented versioned Java Python result contract`, `Completed phased backend and frontend workstreams` (+130 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 183 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Python Optimization Engine FastAPI Microservice` connect `Python Engine` to `Python Engine Engineering`, `Network Optimisation Design`, `Architecture Decision Records`, `System Architecture`, `FastAPI Endpoints`, `ADR-002 Use PostGIS`, `Product Vision and Scope`, `Testing Status`, `Architecture Decision Records`, `System Overview`, `MVP Execution Planning`, `MVP Execution Planning`, `Product Vision and Scope`, `Product Vision and Scope`, `Functional Requirements`, `Non Functional Requirements`, `User Stories`, `2026-08-07`, `Product Vision and Scope`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Why does `Testing Strategy and Current Status` connect `Testing Status` to `Architecture Decision Records`, `FastAPI Endpoints`, `ADR-002 Use PostGIS`, `Product Vision and Scope`, `Python Engine`, `Architecture Decision Records`, `System Overview`, `MVP Execution Planning`, `MVP Execution Planning`, `Product Vision and Scope`, `Non Functional Requirements`, `User Stories`, `2026-08-07`, `2026-08-08`, `2026-08-15`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `SURGE Master Dashboard` connect `MVP Execution Planning` to `Python Engine Engineering`, `Network Optimisation Design`, `Architecture Decision Records`, `System Architecture`, `FastAPI Endpoints`, `ADR-002 Use PostGIS`, `Product Vision and Scope`, `Python Engine`, `Testing Status`, `Architecture Decision Records`, `System Overview`, `MVP Execution Planning`, `Product Vision and Scope`, `Product Vision and Scope`, `Functional Requirements`, `Non Functional Requirements`, `User Stories`, `System Architecture`, `Product Vision and Scope`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **What connects `Implemented end-to-end vertical slice MVP`, `Implemented four deterministic scenarios`, `Verified MVP release gate` to the rest of the system?**
  _135 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Python Engine Engineering` be split into smaller, more focused modules?**
  _Cohesion score 0.07535460992907801 - nodes in this community are weakly interconnected._
- **Should `Network Optimisation Design` be split into smaller, more focused modules?**
  _Cohesion score 0.06755260243632337 - nodes in this community are weakly interconnected._
- **Should `Architecture Decision Records` be split into smaller, more focused modules?**
  _Cohesion score 0.09333333333333334 - nodes in this community are weakly interconnected._

## Extraction audit

Code was extracted locally through AST parsing. Documents were extracted by session subagents, without a paid API call. Actual semantic input/output token counts are unavailable; numeric zero fields are schema placeholders, not measured usage. Documentation requirements, plans, and dated journal entries are source claims, not proof of implemented behavior.

Graph integrity diagnostics: see GRAPH_HEALTH.md. Graphify uses a simple undirected graph, so parallel relationship types can collapse into one edge. Raw extraction is retained in extraction.json, including unresolved endpoints.
