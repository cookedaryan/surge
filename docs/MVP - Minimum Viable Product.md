# Two-Week MVP and AI-Assisted Development Workflow

> **Document status (2026-08-13):** This is a target design, not a statement that every listed capability is API-integrated. SURGE-PY-014 through PY-019 provide PNC assembly, pandapower AC load-flow validation, presentation/GeoJSON packaging, candidate generation, scoring, recommendation, and orchestration. SURGE-PY-020 exposes that workflow through compatible V1 and explicit V2 endpoints and validates a deterministic three-candidate demo. Raw GIS constraint transport/rasterization and ML ranking are post-MVP. See `Surge MVP Ticket Plan.md` for authoritative scope.

The supplied problem statement defines an **enterprise, production-grade platform** for renewable-energy collector and evacuation systems, not merely a shortest-path application.

The complete platform must eventually cover WTG grouping, feeder topology, junctions, pole placement and selection, variable spans, environmental restrictions, cadastral parcels, ROW corridors, lifecycle cost and engineering compliance.

For two developers and two weeks, the correct target is a **complete vertical-slice MVP** that proves this workflow on one controlled project area.

---

# 1. MVP outcome

Given:

- Multiple WTG coordinates
    
- One substation
    
- Elevation data
    
- Roads and accessibility data
    
- Forest and restricted-area layers
    
- Cadastral parcel polygons
    
- Land-compensation rates
    
- Pole and conductor catalogue
    
- WTG electrical loads
    

The system will automatically produce:

1. WTG grouping and feeder assignments
    
2. A preliminary radial collector-network topology
    
3. Candidate feeder routes
    
4. Preliminary junction locations
    
5. Pole positions with variable spans
    
6. Preliminary pole-type recommendations
    
7. ROW corridor polygons
    
8. Affected land parcels and compensation estimates
    
9. Voltage-drop, conductor-loading and power-loss results
    
10. Four optimisation scenarios
    
11. Explainable route-score breakdowns
    
12. GIS and tabular exports
    

This directly addresses the source requirements for collector-network design, multi-objective routing and intelligent pole decisions.

---

# 2. MVP scenarios

Implement these four scenarios:

|Scenario|Primary objective|
|---|---|
|Minimum Cost|Lowest estimated CAPEX and land compensation|
|Minimum Land Impact|Fewest parcels and smallest affected ROW area|
|Minimum Environmental Impact|Lowest forest and restricted-area exposure|
|Balanced|Weighted combination of cost, land, environment and electrical performance|

Keep Minimum Pole Count, Maximum Span, Future Expansion and other advanced scenarios for phase two. The full statement expects those scenario types eventually.

---

# 3. Recommended MVP architecture

```text
                       WEB GIS CLIENT
         Map, WTG input, layers, scenarios, comparison
                              │
                         REST / GeoJSON
                              │
                    JAVA SPRING BOOT API
     Authentication, projects, jobs, persistence, reports
                              │
           ┌──────────────────┴─────────────────┐
           │                                    │
       PostGIS                           Python FastAPI
  Spatial/project data              Optimisation service
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                           GIS engine   Routing engine   Electrical engine
                           GeoPandas    A* / MST         pandapower
                              │              │              │
                              └──────────────┼──────────────┘
                                             │
                                    ML ranking model
                                             │
                               Ranked routes + explanations
```

Spring Boot is suitable for the application layer because it provides production-oriented features such as health checks, metrics and externalised configuration. PostGIS stores GIS geometries, spatial reference information and indexes. GeoPandas provides spatial joins, overlays and geometry operations, while pandapower supports balanced, unbalanced and DC power-flow calculations. ([Home](https://spring.io/projects/spring-boot/?utm_source=chatgpt.com "Spring Boot"))

## Components

### Java application

- Spring Boot REST API
    
- Spring Security with JWT *(planned)*
    
- PostgreSQL/PostGIS
    
- Flyway database migrations
    
- Project and scenario management
    
- Optimisation-job orchestration
    
- Route-result persistence
    
- Audit logs
    
- Report and export generation
    
- Leaflet-based GIS frontend
    

### Python optimisation service

- FastAPI
    
- GeoPandas
    
- Shapely
    
- Rasterio
    
- NumPy
    
- scikit-learn
    
- pandapower
    
- NetworkX or custom graph implementation
    
- pytest
    

### Infrastructure

- Docker Compose
    
- GitHub repository
    
- GitHub Actions *(planned; no workflow exists yet)*
    
- OpenAPI contract
    
- Shared sample dataset
    
- Development and test database
    

---

# 4. Core optimisation pipeline

## Step 1: Validate and standardise data

All uploaded GIS layers must be:

- Geometry validated
    
- Converted to a common projected coordinate system
    
- Clipped to the project boundary
    
- Assigned a layer category
    
- Given a cost or exclusion rule
    

Use projected coordinates measured in metres for routing, buffers, spans and parcel areas.

## Step 2: WTG grouping

Use capacity-constrained clustering:

$$[  
N_f =  
\left\lceil  
\frac{\sum_{i=1}^{n} P_i}  
{P_{\text{feeder,max}}}  
\right\rceil  
]$$

Where:

- (P_i) is the output of WTG (i)
    
- (P_{\text{feeder,max}}) is the feeder capacity
    
- (N_f) is the minimum feeder count
    

MVP approach:

1. Estimate the required number of feeders.
    
2. Apply K-means or agglomerative clustering.
    
3. Reject clusters that violate feeder capacity.
    
4. Move boundary WTGs between clusters until all clusters are valid.
    
5. Generate two or three alternative groupings.
    

## Step 3: Preliminary network topology

For each WTG cluster:

1. Add WTGs and the substation as graph nodes.
    
2. Calculate terrain-aware connection costs.
    
3. Generate a minimum spanning tree.
    
4. Convert MST edges into GIS-routed paths.
    
5. Merge overlapping route segments.
    
6. Treat major merging locations as candidate junctions.
    

This gives a feasible radial MVP topology without attempting a full Steiner-tree implementation.

## Step 4: GIS cost surface

For grid cell (c):

$$
[  
C(c)=  
w_dC_d+  
w_sC_s+  
w_lC_l+  
w_aC_a+  
w_eC_e+  
w_rC_r  
]
$$

Where:

- (C_d): distance cost
    
- (C_s): slope cost
    
- (C_l): land cost
    
- (C_a): accessibility cost
    
- (C_e): environmental cost
    
- (C_r): crossing and construction risk
    

Hard exclusions receive:

$$[  
C(c)=\infty  
]$$

Examples:

- Water bodies
    
- Prohibited forest areas
    
- Defense zones
    
- Dense built-up areas
    
- Impossible slopes
    
- User-defined exclusion polygons
    

## Step 5: Candidate routing

Generate candidate routes using:

- A*
    
- Dijkstra as a validation baseline
    
- Weight perturbation to produce alternatives
    
- Exclusion buffers around previously generated routes
    
- Scenario-specific cost surfaces
    

A* should be the main MVP algorithm. Genetic algorithms and NSGA-II should be deferred until the deterministic pipeline is stable.

## Step 6: Pole placement and variable spans

For each route:

1. Start with the normal span.
    
2. Place mandatory poles at major line-angle changes.
    
3. Place special poles before and after crossings.
    
4. Extend spans within the maximum permitted range.
    
5. Shorten spans on difficult terrain or sharp bends.
    
6. Recalculate the pole count.
    
7. Assign a preliminary pole category.
    

Example rule:

$$[  
L_{\min}\leq L_i\leq L_{\max}  
]$$

Pole classification for the MVP:

- Tangent pole
    
- Angle pole
    
- Terminal pole
    
- Crossing pole
    
- Junction pole
    

The problem statement specifically requires independent span treatment, reduction of unnecessary poles and avoidance of expensive parcels.

**SURGE-PY-010 — Implemented** (`app/algorithms/pole_placement.py`):

- `PolePlacementConfig` carries `target_span_m`, `min_span_m`, `max_span_m`, `angle_pole_threshold_deg`, and `coordinate_tolerance_m` (reserved for future deduplication). All fields validated for finiteness and range.
- Mandatory structures at route start/end (terminal) and at LineString vertices whose deflection angle ≥ `angle_pole_threshold_deg` (angle). Deflection is the angle between the two forward direction vectors at the vertex: 0° straight, 90° right-angle, 180° reversal.
- Section-based span fill: for each section longer than `min_span_m`, the initial span count is `round(L / target_span_m)` using Python's ties-to-even rounding, with a minimum of one. The count is then increased until the arc-length interval is no greater than `max_span_m`. The maximum is a hard limit; the minimum is a subdivision threshold, not a guaranteed lower bound for every result span. A short section receives no fill pole, although its endpoints can still include mandatory angle poles.
- `PoleSpan.span_length_m` is the Euclidean chord distance between adjacent pole Points. Pole IDs are deterministic (`{feeder_id}-P{sequence:03d}`) with a continuous per-feeder sequence across all routes in a batch.
- DEM sag, structural analysis, pole-aware road/river crossings, and network-level pole deduplication are deferred to later tickets. ROW buffering now exists independently in SURGE-PY-011 but is not integrated with pole placement.

**Integration boundary:** PY-010 consumes `RefinedPhysicalRoute` objects and is fully unit-tested as an algorithm module. It is not part of the current `/api/v1/optimise` execution flow, and the optimisation response does not yet expose poles or spans.

## Step 7: ROW and land-parcel analysis

Generate the ROW corridor:

$$[  
P_{\text{ROW}} =  
\operatorname{Buffer}  
\left(  
R,\frac{W_{\text{ROW}}}{2}  
\right)  
]$$

Then intersect it with cadastral parcels:

$$[  
A_i=  
\operatorname{Area}  
\left(  
P_{\text{ROW}}\cap P_i  
\right)  
]$$

Compensation:

$$[  
C_{\text{land}}=  
\sum_{i=1}^{n}A_i r_i  
]
$$
Where:

- (P_i) is parcel (i)
    
- (A_i) is affected area
    
- (r_i) is the compensation rate
    

This must operate on real polygons and multipolygons, not rectangular parcel approximations.

**SURGE-PY-011 — Implemented standalone** (`app/gis/row_analysis.py`):

- Buffers each projected refined route segment by half the configured total ROW width, using explicit flat end caps by default.
- Validates equivalent projected metric CRS provenance for routes and constraints.
- Repairs compatible invalid geometries, rejects unsafe critical features, and indexes validated constraints once with Shapely STRtree.
- Preserves feeder and route-edge identity and separates overlap area, route-centreline exposure, linear-constraint exposure, and boundary-only contact.
- Reports summed segment area and dissolved unique ROW footprint, unique parcels, road crossing events, restricted events, and hard violations.

**Integration boundary:** Constraint GeoJSON is not present in `OptimisationRequest`; the service does not invoke this analysis; results are not transformed to WGS84, returned, persisted, or combined with parcel compensation rates. The implementation proves the projected spatial-analysis core only.

## Step 8: Electrical validation

For each candidate feeder, calculate:

- Feeder current
    
- Conductor loading
    
- Voltage profile
    
- Percentage voltage drop
    
- Active-power losses
    
- Reactive-power flow
    
- Feeder capacity violation
    

Reject candidates when:

- Conductor ampacity is exceeded
    
- Voltage drop exceeds the configured limit
    
- The power flow does not converge
    
- The topology becomes disconnected
    

## Step 9: Explainable ranking

Use a hybrid score:

$$[  
S_{\text{final}}
= 
[ 0.75S_{\text{deterministic}}  
+  
0.25S_{\text{ML}}  
]
]
$$


The ML model may rank valid candidates, but it must not override engineering constraints.

Candidate features:

```text
total_length_km
estimated_capex
pole_count
angle_pole_count
affected_parcel_count
row_area_m2
land_compensation
forest_intersection_m2
road_crossings
river_crossings
average_slope
maximum_slope
accessibility_score
voltage_drop_percent
power_loss_kw
maximum_conductor_loading
```

Use gradient boosting or random forest for the first model. If insufficient historical labelled data exists, use deterministic scoring as the official result and label the ML result as an experimental recommendation.

---

# 5. MVP screens

## Screen 1: Project setup

- Project name
    
- Study-area boundary
    
- WTG upload
    
- Substation selection
    
- Electrical parameters
    

## Screen 2: GIS layers

- Roads
    
- Forest
    
- Water
    
- Parcels
    
- Elevation
    
- Restricted areas
    
- Land rates
    

## Screen 3: Optimisation settings

- Scenario
    
- Cost weights
    
- Feeder capacity
    
- ROW width
    
- Span limits
    
- Maximum voltage drop
    
- Candidate count
    

## Screen 4: Network results

- WTG clusters
    
- Feeder routes
    
- Junctions
    
- Poles
    
- ROW corridors
    
- Impacted parcels
    

## Screen 5: Scenario comparison

| Metric         | Route A | Route B | Route C |
| -------------- | ------: | ------: | ------: |
| Length         |         |         |         |
| Estimated cost |         |         |         |
| Pole count     |         |         |         |
| Parcel count   |         |         |         |
| ROW area       |         |         |         |
| Forest impact  |         |         |         |
| Voltage drop   |         |         |         |
| Power loss     |         |         |         |
| Overall score  |         |         |         |

## Screen 6: Reports

- Route GeoJSON
    
- Pole schedule CSV
    
- Parcel-impact CSV
    
- Route comparison PDF
    
- Electrical-results CSV
    

The final platform is expected to generate route drawings, pole and foundation schedules, BoQ, cost estimates, ROW reports and GIS exports. The MVP should generate preliminary versions of only the route, pole, parcel and cost outputs.

---

# 6. Two-person responsibility split

## Person 1 — Java/backend and platform developer

Owns:

- Spring Boot setup
    
- PostGIS schema
    
- Authentication and RBAC
    
- Organisation and project APIs
    
- WTG and substation APIs
    
- GIS-layer metadata
    
- File-upload workflow
    
- Scenario configuration
    
- Optimisation-job lifecycle
    
- Python-service client
    
- Route-result persistence
    
- Audit logging
    
- Map interface integration
    
- Exports and reports
    
- Docker Compose
    
- Java tests
    

## Person 2 — Python/GIS/ML developer

Owns:

- GIS validation
    
- CRS conversion
    
- Cost-surface generation
    
- Terrain and slope analysis
    
- WTG clustering
    
- Feeder assignment
    
- MST topology
    
- A* and Dijkstra
    
- Candidate-route generation
    
- Pole placement
    
- Variable-span logic
    
- Pole-type rules
    
- ROW buffering
    
- Parcel intersections
    
- Compensation estimation
    
- Electrical validation
    
- ML ranking
    
- Explainability output
    
- Python tests
    

## Shared work

- OpenAPI contract
    
- GIS data model
    
- Engineering assumptions
    
- Acceptance tests
    
- Integration tests
    
- Demo project
    
- Documentation
    
- Release review
    

---

# 7. Two-week implementation schedule

## Week 1 — Build the vertical pipeline

|Day|Java/backend developer|Python/GIS developer|Shared deliverable|
|---|---|---|---|
|1|Spring Boot skeleton, Docker, database|FastAPI skeleton, Python environment|Repository and API contract|
|2|Project, WTG, substation entities|GIS validation and CRS conversion|Valid project dataset accepted|
|3|GIS-layer upload APIs|Terrain, slope and exclusion processing|Normalised GIS workspace|
|4|Optimisation-job APIs|WTG clustering and feeder assignment|WTG groups visible|
|5|Python-service integration|Cost surface, A* and Dijkstra|First feeder route generated|

## Week 2 — Engineering analysis and product integration

|Day|Java/backend developer|Python/GIS developer|Shared deliverable|
|---|---|---|---|
|6|Route and topology persistence|MST topology and alternative routes|Complete radial topology|
|7|GIS result interface|Pole placement and variable spans|Routes and poles displayed|
|8|Scenario comparison APIs|ROW, parcel and compensation analysis|Land-impact results|
|9|Report/export services|pandapower validation and scoring|Validated ranked alternatives|
|10|Authentication, audit logs, UI polish|ML baseline, tests and performance fixes|Demonstrable MVP release|

## Buffer and release work

Use any available remaining calendar days for:

- Integration defects
    
- Sample-data correction
    
- Route-quality tuning
    
- Documentation
    
- Demo recording
    
- Test evidence
    
- Final release tag
    

---

# 8. Role of each development tool

The tools should not all perform the same job.

| Tool          | Authoritative purpose                                             |
| ------------- | ----------------------------------------------------------------- |
| PyCharm       | Python development, debugging, tests and notebooks                |
| IntelliJ IDEA | Java backend development                                          |
| Codex         | Bounded code implementation, refactoring and review               |
| Antigravity   | Planning, cross-repository analysis, browser QA and orchestration |
| Ollama        | Local/private drafting, log analysis and offline review           |
| Obsidian      | Durable engineering knowledge and decision records                |
| NotebookLM    | Source-grounded understanding of specifications and standards     |
| GitHub        | Authoritative code, issues, pull requests and CI                  |

PyCharm now includes core Jupyter support, making it suitable for the Python optimisation service and exploratory GIS notebooks. For the Java developer, use IntelliJ IDEA rather than forcing Spring Boot development through PyCharm. ([JetBrains](https://www.jetbrains.com/help/pycharm/installation-guide.html?utm_source=chatgpt.com "Install PyCharm | PyCharm Documentation"))

Codex can work from local tools or delegated cloud tasks, navigating repositories, editing files, running commands and executing tests. JetBrains also documents Codex as an available integrated agent in its AI Assistant environment, so it may be activated inside PyCharm where supported; otherwise, use the Codex CLI from the IDE terminal. ([OpenAI Help Center](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan.pdf?utm_source=chatgpt.com "Using Codex with your ChatGPT plan | OpenAI Help Center"))

Antigravity 2.0 is now positioned as a standalone agent command centre rather than the primary IDE. It can coordinate agents, execute commands, modify files, use browser automation, perform research and produce verification artifacts. Because it has broad capabilities, use it only inside isolated Git worktrees or containers. ([Google Antigravity](https://www.antigravity.google/docs/overview?utm_source=chatgpt.com "Google Antigravity Documentation"))

Ollama exposes a local API by default and can be called programmatically. Keep it outside the production route-decision path; use it for local assistance and private development tasks. Pin the selected model name and digest in the project configuration so team members use the same local model build. ([Ollama](https://docs.ollama.com/api/introduction?utm_source=chatgpt.com "Introduction - Ollama"))

NotebookLM answers from uploaded sources with inline citations and can generate reports, study guides, mind maps and data tables. Each notebook is independent, so use one shared project notebook rather than splitting related specifications across many notebooks. ([Google Support](https://support.google.com/notebooklm/answer/16164461?utm_source=chatgpt.com "Learn about NotebookLM - Computer - NotebookLM Help"))

---

# 9. Recommended development workflow

```text
Problem statement and standards
             │
             ▼
         NotebookLM
 Requirement extraction, questions, traceability
             │
             ▼
          Obsidian
 Approved requirements, ADRs, assumptions, decisions
             │
             ▼
       GitHub Issue created
 Goal + scope + acceptance tests + files allowed
             │
             ▼
        Antigravity plan
 Architecture impact, task breakdown, browser test plan
             │
             ▼
      Isolated Git branch
             │
             ▼
       Codex implementation
 Code + tests + command results
             │
             ▼
 PyCharm / IntelliJ human review
 Debugging, profiling and engineering verification
             │
             ▼
       Ollama local review
 Logs, documentation and additional test suggestions
             │
             ▼
         CI pipeline
 Unit, integration, lint, security and golden-data tests
             │
             ▼
          Pull request
 Human approval and merge
             │
             ▼
     Obsidian evidence update
 Decision, result, metrics and known limitations
```

---

# 10. Tool-by-tool operating procedure

## A. NotebookLM: requirement and research desk

Create one notebook:

```text
33kV Route Optimisation — Master Sources
```

Upload:

- Problem statement
    
- Approved electrical assumptions
    
- Pole catalogue
    
- Conductor catalogue
    
- GIS data dictionary
    
- Sample cadastral-data description
    
- Applicable engineering references
    
- Meeting notes approved as requirements
    

Use source labels:

```text
Problem Statement
Electrical
Structural
GIS
Land and ROW
Product Requirements
Testing
```

Ask NotebookLM:

```text
Extract every mandatory capability and create a traceability table with:
requirement, source section, MVP status, implementation module,
acceptance test and deferred work.
```

Do not upload confidential parcel-owner details to a personal consumer notebook. For sensitive organisational material, use an approved Workspace configuration or keep the source local. Google documents stronger enterprise handling for qualifying Workspace accounts. ([Google Support](https://support.google.com/notebooklm/answer/16337734?hl=en&utm_source=chatgpt.com "Use NotebookLM with a work or school Google account - NotebookLM Help"))

### NotebookLM output rule

NotebookLM output is research material, not an approved requirement.

Promotion path:

```text
NotebookLM finding
→ human verification against citation
→ approved Obsidian note
→ GitHub issue
```

---

## B. Obsidian: project memory

Use one vault:

```text
33kV-Route-Platform/
├── 00-Inbox/
├── 01-Problem-Statement/
├── 02-Requirements/
├── 03-Architecture/
├── 04-Domain-Rules/
├── 05-Algorithms/
├── 06-Data-Dictionary/
├── 07-ADRs/
├── 08-Experiments/
├── 09-Test-Evidence/
├── 10-Meetings/
├── 11-Daily-Logs/
├── 12-Demo/
└── Templates/
```

Recommended note types:

- Requirement
    
- Architecture Decision Record
    
- Engineering assumption
    
- Experiment
    
- Defect analysis
    
- Dataset record
    
- Model record
    
- Release note
    

### Requirement note template

```yaml
---
id: REQ-ROUTE-001
status: approved
source: Problem Statement
module: routing-engine
owner: python
priority: must
verification: integration-test
---
```

```text
# Requirement

# Engineering interpretation

# Acceptance criteria

# Source evidence

# Implementation links

# Test evidence

# Open risks
```

Use Obsidian for decisions and reasoning, but keep actual development tasks in GitHub Issues. Obsidian supports cross-application automation through its URI scheme; Obsidian Sync can provide version history and end-to-end encryption when configured appropriately. ([Obsidian Help](https://help.obsidian.md/Extending%2BObsidian/Obsidian%2BURI?utm_source=chatgpt.com "Obsidian URI - Obsidian Help"))

---

## C. Antigravity: planner and verifier

Use Antigravity before implementation for:

- Cross-service architecture analysis
    
- Breaking an epic into issues
    
- Database/API impact analysis
    
- UI flow planning
    
- Browser-based map testing
    
- Reviewing screenshots and test artifacts
    
- Release-readiness checks
    
- Comparing implementation with requirements
    

Do not use Antigravity to make uncontrolled edits directly on the active developer branch.

### Antigravity task format

```text
Analyse issue ROUTE-014.

Read:
- AGENTS.md
- docs/domain-rules.md
- contracts/openapi.yaml
- the issue acceptance criteria

Produce:
1. impacted modules,
2. implementation sequence,
3. database/API changes,
4. test cases,
5. risks,
6. an explicit list of files that may be edited.

Do not modify code during the planning pass.
```

For a code-changing Antigravity task:

```text
git worktree add ../worktrees/route-014 -b agent/route-014
```

Only that worktree may be modified.

---

## D. Codex: implementation agent

Codex should receive one bounded issue at a time.

Good tasks:

- Implement one endpoint
    
- Add one cost-layer processor
    
- Add route-feature extraction
    
- Add a unit-test suite
    
- Refactor a module without behaviour changes
    
- Review one pull request
    
- Fix one reproducible bug
    

Bad tasks:

- “Build the complete platform”
    
- “Improve the algorithm”
    
- “Make the app industry grade”
    
- “Change anything necessary”
    

### Codex implementation packet

```text
Issue: ROUTE-014
Goal: Generate ROW corridor polygons and parcel intersections.

Read first:
- AGENTS.md
- docs/domain-rules.md
- contracts/openapi.yaml
- docs/acceptance-tests/route-014.md

Allowed modules:
- optimisation-python/app/row/
- optimisation-python/tests/row/

Do not modify:
- database migrations
- API contracts
- electrical calculations

Acceptance criteria:
1. Buffer width is interpreted in metres.
2. Multipolygon parcels are supported.
3. Invalid geometries are repaired or rejected explicitly.
4. Output includes affected area per parcel.
5. Unit tests cover no intersection, partial intersection and multiple parcels.
6. Run formatting, type checks and tests.

Return:
- files changed,
- commands executed,
- test results,
- unresolved assumptions.
```

Human developers must review every generated diff.

---

## E. PyCharm: Python authoritative workspace

Recommended PyCharm setup:

```text
Interpreter: project .venv
Test runner: pytest
Formatter: Ruff format or Black
Linter: Ruff
Type checker: mypy
Notebook support: enabled
Docker Compose services: attached
Environment variables: loaded from local .env
```

Run configurations:

```text
FastAPI Development
Python Unit Tests
GIS Integration Tests
Routing Benchmark
Electrical Validation
Training Pipeline
Full Python Quality Gate
```

Use notebooks only for exploration:

```text
notebooks/
├── 01_data_validation.ipynb
├── 02_cost_surface_experiment.ipynb
├── 03_clustering_experiment.ipynb
├── 04_routing_benchmark.ipynb
└── 05_model_evaluation.ipynb
```

No production algorithm should remain only inside a notebook. Promote stable code into `src/` with unit tests.

---

## F. Ollama: local private assistant

Recommended tasks:

- Summarise long test logs
    
- Explain stack traces
    
- Generate additional edge-case ideas
    
- Draft docstrings
    
- Compare API request and response schemas
    
- Search locally exported engineering notes
    
- Review whether test names match acceptance criteria
    
- Convert experiment notes into draft documentation
    

Do not let Ollama:

- Approve engineering feasibility
    
- Select the official route
    
- Alter cost values
    
- Invent electrical limits
    
- Generate final compliance claims
    
- Merge code automatically
    

Optional local review script:

```text
Git diff
   ↓
Remove secrets and large binary data
   ↓
Send diff + acceptance criteria to Ollama
   ↓
Receive review suggestions
   ↓
Developer verifies each suggestion
```

Record the local model configuration:

```yaml
ollama:
  model: <pinned-model-tag>
  digest: <recorded-digest>
  temperature: 0.1
  purpose: local-review-only
```

---

# 11. Repository structure

```text
33kv-route-platform/
├── AGENTS.md
├── README.md
├── compose.yaml
├── .env.example
├── backend-java/
│   ├── src/
│   ├── build.gradle
│   └── Dockerfile
├── optimisation-python/
│   ├── app/
│   │   ├── algorithms/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── notebooks/
│   ├── pyproject.toml
│   └── Dockerfile
├── web-map/
├── contracts/
│   ├── openapi.yaml
│   ├── schemas/
│   └── examples/
├── database/
│   └── migrations/
├── sample-data/
│   ├── public-demo/
│   └── README.md
├── docs/
│   ├── architecture.md
│   ├── domain-rules.md
│   ├── data-dictionary.md
│   ├── acceptance-tests/
│   └── adr/
└── tools/
    ├── validate_dataset.py
    ├── benchmark_routes.py
    └── local_review.py
```

---

# 12. Branch and agent rules

```text
main
└── develop
    ├── feature/java-project-api
    ├── feature/python-cost-surface
    ├── agent/route-014
    └── fix/parcel-intersection
```

Mandatory rules:

1. One issue per branch.
    
2. One code-changing agent per branch.
    
3. Codex and Antigravity never modify the same worktree simultaneously.
    
4. Agents never work directly on `main` or `develop`.
    
5. Database migrations require human review.
    
6. API contract changes require both developers.
    
7. Secrets and private GIS data stay outside prompts.
    
8. Generated code must include tests.
    
9. Route-algorithm changes must pass golden-dataset tests.
    
10. All merges require a human-reviewed pull request.
    

---

# 13. CI quality gates

## Python

```text
ruff check
ruff format --check
mypy
pytest
GIS golden-dataset test
Routing benchmark
Electrical-validation test
```

## Java

```text
compile
unit tests
integration tests
architecture tests
database migration test
OpenAPI compatibility test
```

## System

```text
Docker image build
Service health checks
End-to-end optimisation test
GeoJSON schema validation
Security/dependency scan
Demo-dataset run
```

---

# 14. Golden demonstration dataset

Create one small controlled dataset containing:

- 8–12 WTGs
    
- One substation
    
- Two likely feeder groups
    
- One forest exclusion
    
- One high-cost land parcel
    
- One road crossing
    
- One water crossing
    
- Irregular parcel polygons
    
- A DEM with moderate slopes
    
- At least two feasible route corridors
    

Expected system behaviour:

- Produce at least two feeders
    
- Avoid hard exclusions
    
- Generate at least three valid alternatives
    
- Show different winners across scenarios
    
- Place poles with non-uniform spans
    
- Calculate ROW-parcel intersections
    
- Reject at least one electrically invalid candidate
    
- Explain why the balanced route ranked first
    

---

# 15. Definition of done

The MVP is complete only when:

- A user can create a project.
    
- Multiple WTGs and a substation can be loaded.
    
- GIS layers can be uploaded and validated.
    
- WTGs are automatically grouped.
    
- Feeder topology is generated.
    
- At least three route alternatives are produced.
    
- Hard constraints are respected.
    
- Poles and spans are generated.
    
- ROW polygons and affected parcels are calculated.
    
- Preliminary electrical validation runs.
    
- Four scenarios can be compared.
    
- Every score displays its contributing metrics.
    
- Selected results can be exported.
    
- The complete pipeline runs through Docker Compose.
    
- Unit, integration and golden-data tests pass.
    
- Known assumptions and limitations are documented.
    

The final problem statement evaluates optimisation quality, engineering feasibility, explainability, scalability and integrated usability. The MVP should provide measurable evidence for all five, while clearly marking structural design, final foundations, statutory approval and production-scale optimisation as post-MVP work.
