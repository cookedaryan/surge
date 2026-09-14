# Graph Report - surge  (2026-09-11)

## Corpus Check
- 219 files · ~162,958 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2419 nodes · 7821 edges · 132 communities (98 shown, 22 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1123 edges (avg confidence: 0.94)
- Token cost: 512,803 input · 0 output

## Community Hubs (Navigation)
- Orchestrator & Search Cache
- Candidate Scoring Models
- WTG Grouping & Topology Search
- Right-of-Way Corridor Analysis
- Pole Placement Tests
- Feeder Validation & Voltage Drop
- Scenario Models & PNC Errors
- Route Refinement
- ML Pre-Ranker Pipeline
- Cable Sizing & Repair
- Load Flow Execution
- PNC Assembly Tests
- PNC Assembly & Route Graph
- Route Scoring
- Land Decision & Fingerprinting
- Presentation Load Results
- Cost Catalogue & Lifecycle
- Decision Report Builder
- Physical Routing Feasibility
- Pole Micro-Siting
- Engineering Metrics
- Route Graph Scenario Tests
- Decision Report Models
- V2 Optimise Schemas
- Legacy Schema Mapping
- Repair Diagnostics
- GIS Constraint Application
- Presentation GeoJSON
- Report Sections
- Repair Exhaustion
- Pole Placement Algorithms
- Feeder Validation Tests
- Candidate Generation Tests
- Cost Surface
- Optimise API Tests
- Engineering Report Tests
- Scenario Config Validation
- Presentation Models
- Scenario Strategy Tests
- MVP Tickets & Scoring Docs
- Constraint Layer Validation
- Legacy Optimise Endpoint Tests
- A-Star Pathfinding
- GIS Preprocessing Tests
- API v1 & App Config
- Canonical Metrics Spec
- Fixture Determinism & Stack
- Web Map Redesign Plan
- Optimise API Contract Tests
- Pole Deduplication Tests
- ADR-007 Load Flow Validation
- Constraint Routing Gap Plan
- CRS Transformation
- Land Acquisition Routing Docs
- MVP Gap Closure Tickets
- CI Gates & Spec Alignment
- Engine Stack & Topology Docs
- Engine Architecture Docs
- PNC Assembly Boundary Docs
- Engine Integration Plan
- Load Flow Convergence Tests
- GeoJSON Parsing
- Lifecycle Cost Tests
- Explainability & ML Ranking
- SURGE Ticket Plan Docs
- V2 Schema Validators
- Pole Placement Micro Tests
- TRD Pipeline Contracts
- Corpus Provenance & Scenarios
- Scoring Gap Findings
- Land CAPEX & Pole Costs
- Scenario Structural Integrity
- Report Renderers
- Screen Flow & Sync Docs
- Java/Python Boundary Docs
- Route Scoring Architecture Docs
- KMZ Asset Classification
- UX Improvement Report
- PRD Routing Requirements
- API v2 Endpoints
- GIS Preprocessing
- Demo Data & Transparency
- PRD Domain Glossary
- Land Acquisition Consumption Gap
- Gap Closure Cost Findings
- Integration & Ticket Plan Docs
- Synthetic Corpus Provenance
- Scenario Variation Tests
- Cost Model Catalogue Docs
- GIS Geometry Validation
- Scenario Determinism Tests
- Parameter Schedule Tests
- Duplicate Suppression Tests
- Candidate PNC Scenario Docs
- Consumption Gap Phases
- Pole Micro-Siting Helpers
- PNC Assembly Reverse Mapping
- MVP Gap Closure Findings
- PNC Assembly BFS
- Reporting Schema Version
- Candidate Diversity Tests
- MVP Scope Isolate
- Engine Architecture Isolate
- Engine Integration Isolate
- Redesign Spec Isolate
- Cost Function Helpers
- Electrical Analysis Helpers
- Core Package Init
- Costing Package Init
- App Package Init
- Land Package Init
- Reporting Package Init
- Schemas Package Init
- Coordinate Transform Utils
- Engineering Metrics Tests
- App Flow Isolate
- Consumption Gap Isolate
- Route Scoring Isolate
- PRD Minimum Cost Isolate
- PRD Minimum Cost Node

## God Nodes (most connected - your core abstractions)
1. `ProjectSpatialData` - 166 edges
2. `CostSurface` - 140 edges
3. `LoadFlowConfig` - 98 edges
4. `ProjectPNCNetwork` - 81 edges
5. `CollectorTopologyResult` - 78 edges
6. `WindTurbine` - 70 edges
7. `LoadFlowNetworkResult` - 59 edges
8. `generate_pnc_scenarios()` - 59 edges
9. `optimise_project()` - 56 edges
10. `LoadFlowCableType` - 52 edges

## Surprising Connections (you probably didn't know these)
- `PNC Assembly Fail-Loud Failure Model` --rationale_for--> `build_pnc_network()`  [EXTRACTED]
  docs/artifacts/PNC Network Assembly.md → optimisation-python/app/pnc/assembly.py
- `Corpus Generation Fixtures` --semantically_similar_to--> `Golden Demonstration Dataset`  [INFERRED] [semantically similar]
  optimisation-python/tests/fixtures/README.md → docs/TRD.md
- `Provenance Vocabulary` --semantically_similar_to--> `Explainability`  [INFERRED] [semantically similar]
  optimisation-python/tests/fixtures/corpus/PROVENANCE.md → docs/PRD.md
- `app.pnc Orchestration Package` --implements--> `build_pnc_network()`  [EXTRACTED]
  docs/artifacts/PNC Network Assembly.md → optimisation-python/app/pnc/assembly.py
- `build_pnc_network()` --references--> `ProjectPNCNetwork`  [EXTRACTED]
  optimisation-python/app/pnc/assembly.py → docs/artifacts/PNC Network Assembly.md

## Import Cycles
- 3-file cycle: `optimisation-python/app/optimisation/__init__.py -> optimisation-python/app/optimisation/orchestrator.py -> optimisation-python/app/optimisation/candidate_evaluation.py -> optimisation-python/app/optimisation/__init__.py`
- 4-file cycle: `optimisation-python/app/optimisation/__init__.py -> optimisation-python/app/optimisation/orchestrator.py -> optimisation-python/app/optimisation/candidate_search.py -> optimisation-python/app/optimisation/candidate_evaluation.py -> optimisation-python/app/optimisation/__init__.py`

## Hyperedges (group relationships)
- **Four MVP Optimisation Scenarios** — docs_prd_minimum_cost, docs_prd_minimum_land_impact, docs_prd_minimum_environmental_impact, docs_prd_balanced, docs_prd_multi_objective_optimization [EXTRACTED 1.00]
- **Six-Screen SURGE User Journey** — docs_app_flow_screen_1_project_setup, docs_app_flow_screen_2_gis_layers, docs_app_flow_screen_3_optimisation_settings, docs_app_flow_screen_4_network_results, docs_app_flow_screen_5_scenario_comparison, docs_app_flow_screen_6_reports, docs_app_flow_high_level_journey [EXTRACTED 1.00]
- **Deterministic ML Training Corpus Fixture Family** — optimisation_python_tests_fixtures_readme_syn_1_clustered_8, optimisation_python_tests_fixtures_readme_syn_2_spread_12, optimisation_python_tests_fixtures_readme_syn_3_clustered_20, optimisation_python_tests_fixtures_readme_syn_4_spread_30, optimisation_python_tests_fixtures_readme_syn_5_mixed_40, optimisation_python_tests_fixtures_readme_synthetic_projects_generator, optimisation_python_tests_fixtures_readme_deterministic_seed_42 [EXTRACTED 1.00]
- **Pandapower Load-Flow Validation Stack** — docs_artifacts_adr_007_pandapower_ac_load_flow_validation_adr_007, docs_artifacts_ac_load_flow_validation_load_flow_cable_type, docs_artifacts_ac_load_flow_validation_load_flow_config, docs_artifacts_ac_load_flow_validation_wtg_operating_point, docs_artifacts_ac_load_flow_validation_deterministic_builder, docs_artifacts_ac_load_flow_validation_newton_raphson_solver [EXTRACTED 1.00]
- **Candidate Evaluation Pipeline: Generation to Recommendation** — docs_artifacts_mvp_minimum_viable_product_surge_py_017, docs_artifacts_ac_load_flow_validation_newton_raphson_solver, docs_artifacts_canonical_candidate_engineering_metrics_surge_py_026, docs_artifacts_multi_objective_candidate_scoring_surge_py_027, docs_artifacts_multi_objective_candidate_scoring_surge_py_029, docs_artifacts_mvp_minimum_viable_product_surge_py_018 [EXTRACTED 1.00]
- **Consumption Gap Phase 3 Cost Tickets** — docs_artifacts_consumption_gap_ticket_plan_ticket_p_1, docs_artifacts_consumption_gap_ticket_plan_ticket_c_1, docs_artifacts_consumption_gap_ticket_plan_ticket_f_1, docs_artifacts_consumption_gap_ticket_plan_ticket_c_2, docs_artifacts_consumption_gap_ticket_plan_ticket_c_3, docs_artifacts_consumption_gap_ticket_plan_ticket_c_4 [EXTRACTED 1.00]
- **Frozen MVP Vertical-Slice Ticket Sequence (PY-014 to PY-020)** — docs_artifacts_surge_mvp_ticket_plan_mvp_freeze_py_020 [EXTRACTED 1.00]
- **End-to-End Optimisation Pipeline Stages** — docs_artifacts_python_engine_architecture_py_006, docs_artifacts_python_engine_architecture_py_007, docs_artifacts_python_engine_architecture_py_008, docs_artifacts_python_engine_architecture_py_009, docs_artifacts_pnc_network_assembly_project_pnc_network, docs_artifacts_presentation_boundary_build_project_result [EXTRACTED 1.00]
- **Track A - Unreachable Python Capabilities to Expose** — docs_artifacts_python_engine_integration_plan_track_a, docs_artifacts_python_engine_integration_plan_a1_emit_cable_sizing, docs_artifacts_python_engine_integration_plan_a2_emit_land_decision, docs_artifacts_python_engine_integration_plan_a3_reachable_micro_siting, docs_artifacts_python_engine_integration_plan_a4_expose_engineering_report [EXTRACTED 1.00]

## Communities (132 total, 22 thin omitted)

### Community 0 - "Orchestrator & Search Cache"
Cohesion: 0.06
Nodes (97): CandidateElectricalEvaluationError, Exception, Execution error evaluating an individual candidate network. This indicates a…, Electrical feasibility screening and validation., evaluate_candidate(), Evaluate one candidate's electrical, engineering, and lifecycle results., _apply_land_routing_constraints(), _compute_electrical_context_id() (+89 more)

### Community 1 - "Candidate Scoring Models"
Cohesion: 0.08
Nodes (84): NormalizationRange, CandidateCostAssessment, CandidateLifecycleCost, Re-scores the entire eligible archive and updates their evaluation results., _score_archive(), CandidateEngineeringMetrics, Raw engineering quantities extracted for one PNC candidate., End-to-End Optimisation package for Surge. Public API ----------… (+76 more)

### Community 2 - "WTG Grouping & Topology Search"
Cohesion: 0.07
Nodes (84): build_feeder_mst(), Graph, Builds a radial minimum spanning tree (MST) for each feeder group assigned in…, FeederAssignment, FeederGroupingResult, group_wtgs(), Uses scipy.optimize.milp to solve the capacitated assignment problem.…, Solve the capacitated assignment problem with an explicit balance objective.… (+76 more)

### Community 3 - "Right-of-Way Corridor Analysis"
Cohesion: 0.06
Nodes (74): analyse_row_corridors(), _build_corridor(), _build_corridors(), ConstraintFeature, _count_point_geometries(), _count_road_crossings(), _deduplicate_coordinates(), _intersect_corridor() (+66 more)

### Community 4 - "Pole Placement Tests"
Cohesion: 0.07
Nodes (68): calculate_span_count(), place_poles_on_route(), PolePlacementConfig, Immutable configuration for the pole placement engine. All numeric fields must…, Return the number of spans needed to cover *route_length_m* while respecting…, Place physical pole structures along a single refined feeder route. Parameters…, default_config(), make_route() (+60 more)

### Community 5 - "Feeder Validation & Voltage Drop"
Cohesion: 0.07
Nodes (53): _build_route_map(), calculate_downstream_active_power_mw(), _edge_key(), _evaluate_feeder(), _evaluate_turbines(), _project_nodes(), CRS, DiGraph (+45 more)

### Community 6 - "Scenario Models & PNC Errors"
Cohesion: 0.07
Nodes (41): GroupingObjective, StrEnum, Controls the feeder-assignment objective used during WTG grouping.…, AttemptOutcome, NoValidScenarioError, StrEnum, Domain models for SURGE-PY-017 candidate PNC scenario generation. All models…, Complete description of algorithm inputs for one candidate scenario. Every… (+33 more)

### Community 7 - "Route Refinement"
Cohesion: 0.10
Nodes (55): Coordinate, PhysicalRoute, PhysicalRoutingResult, _axis_breakpoints(), _cells_touching_grid_point(), _coordinate_is_within_surface(), _cost_is_not_greater(), _existing_cells_touching_grid_point() (+47 more)

### Community 8 - "ML Pre-Ranker Pipeline"
Cohesion: 0.08
Nodes (45): NamedTuple, ArtifactMetadata, load_artifact(), Any, Path, Pipeline, save_artifact(), ValidationSummary (+37 more)

### Community 9 - "Cable Sizing & Repair"
Cohesion: 0.08
Nodes (46): _aggregate_downstream_power(), CableSizingResult, _edge_key(), NoFeasibleCableError, DiGraph, EdgeKey, Exception, Deterministic per-segment cable sizing. (+38 more)

### Community 10 - "Load Flow Execution"
Cohesion: 0.10
Nodes (45): build_pandapower_network(), Pandapower electrical network builder for AC load flow., Strict input validation prior to network construction. Raises ValueError on any…, Build a pandapower electrical network from a PNC network. Validates inputs…, _validate_inputs(), LoadFlowConfig, Overall AC load flow configuration for a project simulation. Includes global…, PandapowerBuildResult (+37 more)

### Community 11 - "PNC Assembly Tests"
Cohesion: 0.11
Nodes (21): CostSurface, ProjectSpatialData, build_pnc_network(), Construct and return a ``ProjectPNCNetwork`` from validated inputs. Callers…, Run the complete pipeline and return a validated PNC network. Executes WTG…, cost_surface(), _make_project(), fixture (+13 more)

### Community 12 - "PNC Assembly & Route Graph"
Cohesion: 0.11
Nodes (32): Helper to ensure globally unique string IDs for Substations., Helper to ensure globally unique string IDs for WTGs., substation_node_id(), turbine_node_id(), RefinedRoutingResult, assemble_pnc_network(), _build_pnc_network(), _collect_wtg_coordinates() (+24 more)

### Community 13 - "Route Scoring"
Cohesion: 0.13
Nodes (44): CandidateScore, CriterionScore, evaluate_network_candidates(), NetworkCandidateMetrics, NormalizationRange, Score, normalize, and rank comparable network-level route candidates.…, RouteScoringResult, RouteScoringWeights (+36 more)

### Community 14 - "Land Decision & Fingerprinting"
Cohesion: 0.14
Nodes (41): LifecycleCostConfig, _aggregate_cost_basis(), assess_candidate_land(), _assess_parcel(), assess_transaction_option(), present_value_factor(), Decimal, Deterministic commercial decisions for candidate parcel exposures. (+33 more)

### Community 15 - "Presentation Load Results"
Cohesion: 0.12
Nodes (44): Pandapower electrical AC load flow solver and analysis., Pandapower-based AC load flow validation module., LoadFlowBusResult, LoadFlowFeederResult, LoadFlowNetworkResult, LoadFlowSegmentResult, LoadFlowViolation, LoadFlowViolationCode (+36 more)

### Community 16 - "Cost Catalogue & Lifecycle"
Cohesion: 0.09
Nodes (31): CostCatalogueProvider, JSONCatalogueProvider, Catalogue resolution interface., Resolve a cost catalogue by its identifier. Raises: CostConfigurationError: if…, CostConfigurationError, CostEvaluationFailure, CostEvaluationFailureCode, StrEnum (+23 more)

### Community 17 - "Decision Report Builder"
Cohesion: 0.10
Nodes (40): ElectricalSummary, Bind a cached evaluation to a materialized scenario identity., CandidateWorkflowResult, _active_loss(), _build_comparisons(), _build_economics_summary(), _build_electrical_summary(), _build_land_summary() (+32 more)

### Community 18 - "Physical Routing Feasibility"
Cohesion: 0.11
Nodes (39): Graph, ValueError, Validates that the cost surface is suitable for A* routing., Translates electrical MST edges into physical LineString paths using A* across…, route_collector_topology(), RouteNotFoundError, validate_cost_surface(), CollectorTopologyResult (+31 more)

### Community 19 - "Pole Micro-Siting"
Cohesion: 0.12
Nodes (39): _generate_candidates(), _is_feasible(), _network_objective(), optimize_poles(), _owners_for_parcels(), _parcel_layers_for_point(), PoleMicroSitingContext, PoleMicroSitingMove (+31 more)

### Community 20 - "Engineering Metrics"
Cohesion: 0.12
Nodes (34): CandidateEngineeringAssessment, CandidateSpatialResult, EngineeringMetricFailure, EngineeringMetricFailureCode, ParcelEngineeringExposure, StrEnum, Canonical candidate-level engineering metric domain models., Complete metrics or explicit extraction failures for one candidate. (+26 more)

### Community 21 - "Route Graph Scenario Tests"
Cohesion: 0.08
Nodes (28): build_project_graph(), Graph, Constructs an undirected complete topology graph from project spatial data.…, mock_crs(), CRS, fixture, sample_project(), test_complete_graph_edge_count() (+20 more)

### Community 22 - "Decision Report Models"
Cohesion: 0.14
Nodes (26): CandidateSearchResult, Evidence from the search process., Backward-compatible alias for the proposal count., Backward-compatible alias for duplicate proposals., Count candidates served by evaluation or exact cache reuse., Backward-compatible alias for failed search candidates., OptimisationWorkflowResult, build_decision_report() (+18 more)

### Community 23 - "V2 Optimise Schemas"
Cohesion: 0.16
Nodes (30): Map domain workflow results securely back to API boundaries., Expose the per-parcel land decisions, not only the totals., to_api_response(), _to_land_summary(), ApiModel, CandidateCostSummary, CandidateLandSummary, CandidateSummary (+22 more)

### Community 24 - "Legacy Schema Mapping"
Cohesion: 0.14
Nodes (27): post, run_optimisation(), _compatibility_cable_config(), _legacy_message(), _legacy_pole_collection(), _legacy_route_collection(), Any, Derive the cable ampacity needed to retain the legacy feeder-capacity input. (+19 more)

### Community 25 - "Repair Diagnostics"
Cohesion: 0.16
Nodes (30): ClosedLoopRepairResult, RepairAction, RepairReason, _describe_exhaustion_reason(), _describe_repair_failure(), _effective_ampacity_a(), Any, Say why no conductor upgrade was made, where the loop knows and the reader… (+22 more)

### Community 26 - "GIS Constraint Application"
Cohesion: 0.16
Nodes (27): apply_avoidance_constraints(), apply_constraint_layers(), ConstraintLayer, ConstraintMode, ConstraintType, effective_constraint_geometry(), StrEnum, Return the buffered geometry used by routing and compliance checks. (+19 more)

### Community 27 - "Presentation GeoJSON"
Cohesion: 0.16
Nodes (20): Reuse PNC GeoJSON Conversion, network_to_feature_collection(), Any, CRS, Convert a ``ProjectPNCNetwork`` to a GeoJSON FeatureCollection. Parameters…, ProjectPNCNetwork, The complete automatically assembled Project PNC Network. Attributes ----------…, build_enriched_geojson() (+12 more)

### Community 28 - "Report Sections"
Cohesion: 0.29
Nodes (16): DecisionReport, build_engineering_report(), Builds the final engineering report sections from a DecisionReport., build_alternatives(), build_economics(), build_electrical(), build_executive_summary(), build_land() (+8 more)

### Community 29 - "Repair Exhaustion"
Cohesion: 0.19
Nodes (25): StrEnum, Which of the loop's dead ends ended the repair. ``REPAIR_EXHAUSTED`` is…, RepairExhaustionReason, RepairStatus, _config(), _invalid_result(), _network(), MonkeyPatch (+17 more)

### Community 30 - "Pole Placement Algorithms"
Cohesion: 0.13
Nodes (24): _can_join_endpoint_cluster(), _classify_pole(), _deduplicate_distances(), deduplicate_pole_endpoints(), _deflection_angle_deg(), _endpoint_pole_records(), _EndpointPoleRecord, _physical_pole_from_endpoint_cluster() (+16 more)

### Community 31 - "Feeder Validation Tests"
Cohesion: 0.22
Nodes (23): RefinedPhysicalRoute, Validate one complete radial collector network at a fixed operating point.…, validate_collector_network(), _validate_route_coverage(), ConductorElectricalProperties, ElectricalDesignConfig, Positive ampacity and non-negative series impedance per kilometre., Operating point, voltage limit, and conductor used by the proxy. (+15 more)

### Community 32 - "Candidate Generation Tests"
Cohesion: 0.14
Nodes (8): generate_pnc_scenarios(), Generate a configurable set of deterministic PNC network candidates. If…, SCN-001, SCN-002, SCN-003 with complete ProjectPNCNetworks., Two identical runs produce identical IDs in identical order., TestConfigurableCandidateCount, TestDefaultCandidateGeneration, TestStableScenarioIds, _PSD

### Community 33 - "Cost Surface"
Cohesion: 0.16
Nodes (22): build_project_cost_surface(), grid_to_world(), Convert geographic (projected) coordinates (x, y) to grid cell indices (row,…, Convert grid cell indices (row, col) to the centre of the cell in world…, Creates a CostSurface covering the full project extent (WTGs + Substation)., world_to_grid(), mock_project(), fixture (+14 more)

### Community 34 - "Optimise API Tests"
Cohesion: 0.17
Nodes (21): OptimiseProjectResponse, _costing_config(), mvp_v2_payload(), fixture, JsonObject, MonkeyPatch, parametrize, The land engine's conclusions have to leave the process. Only… (+13 more)

### Community 35 - "Engineering Report Tests"
Cohesion: 0.16
Nodes (20): CandidateSearchStatistics, StrEnum, Statistics for the candidate search process., SearchTerminationReason, AlternativeSummary, OptimizationEvidence, ReportWarning, The base_report fixture must use the centralised schema version constant. If… (+12 more)

### Community 36 - "Scenario Config Validation"
Cohesion: 0.14
Nodes (8): InvalidScenarioConfigError, Configuration for deterministic PNC scenario generation. Attributes ----------…, Raised when ``ScenarioGenerationConfig`` validation fails., ScenarioGenerationConfig, A project that can only produce one unique PNC topology., TestConfigValidation, TestConstrainedProject, TestSingleWTGProject

### Community 37 - "Presentation Models"
Cohesion: 0.22
Nodes (16): Exceptions for the presentation boundary layer., Presentation layer for creating map-ready JSON result boundaries., ElectricalSummary, FeederResult, NetworkSummary, PoleSummary, PresentationModel, ProjectOptimizationResult (+8 more)

### Community 38 - "Scenario Strategy Tests"
Cohesion: 0.13
Nodes (9): _make_diverse_project(), fixture, When routing fails for a candidate, the attempt is recorded as ROUTING_FAILED…, 12 WTGs spread across the large cost surface in 3 clusters. Designed to allow 3…, For the diverse 12-WTG project, the balanced strategy should produce a feeder…, TestBalancedCandidatesRespectCapacity, TestBalanceStrategyImproves, TestBaseGraphNotMutated (+1 more)

### Community 39 - "MVP Tickets & Scoring Docs"
Cohesion: 0.12
Nodes (19): Candidate PNC Scenario Generation, PY-017 Completion Boundary, R-1 Candidate Comparison on Success, Baseline Scenario Comparison, Multi-Objective Candidate Scoring, RecommendationReason, SURGE-PY-029 Cost-Aware Scoring, TRADE_OFF_ACCEPTED Disclosure (+11 more)

### Community 40 - "Constraint Layer Validation"
Cohesion: 0.23
Nodes (18): _as_finite_number(), _constraint_mode(), _constraint_type(), ConstraintApplication, ingest_avoidance_constraints(), _layer_id(), _normalize_token(), _numeric_property() (+10 more)

### Community 41 - "Legacy Optimise Endpoint Tests"
Cohesion: 0.19
Nodes (18): legacy_to_workflow_invocation(), Map the Java-compatible V1 request into the canonical workflow input., create_payload(), Any, The land engine is reached through v1 as well as v2. Java calls v1, and v1 is…, Every existing caller sends no land context and must keep working., test_coincident_route_endpoints_return_422(), test_empty_wtg_collection() (+10 more)

### Community 42 - "A-Star Pathfinding"
Cohesion: 0.20
Nodes (16): a_star(), AStarResult, GridCell, empty_surface(), fixture, test_astar_is_deterministic(), test_corner_cutting_prevented(), test_diagonal_distance_cost() (+8 more)

### Community 43 - "GIS Preprocessing Tests"
Cohesion: 0.35
Nodes (17): process_project_data(), Parses WTG and Substation GeoJSON, verifies geometries, calculates a common…, _make_fc(), _make_pt(), Any, test_blank_ids(), test_duplicate_ids(), test_empty_wtg_rejected() (+9 more)

### Community 44 - "API v1 & App Config"
Cohesion: 0.15
Nodes (8): BaseSettings, FastAPI, get, health_check(), API endpoints package., get_settings(), Settings, create_application()

### Community 45 - "Canonical Metrics Spec"
Cohesion: 0.13
Nodes (17): Newton-Raphson Load-Flow Solver (runpp), Graceful Non-Convergence, All-or-Nothing Metric Availability, Cached CollectorPoleResult Reuse, CandidateEngineeringAssessment, CandidateEngineeringMetrics, Canonical Candidate Engineering Metrics (PY-026), POLE_CONFIG_MISSING Reason Code (+9 more)

### Community 46 - "Fixture Determinism & Stack"
Cohesion: 0.12
Nodes (17): Determinism Requirement, electrical_analysis.py Placeholder, GeoPandas Vector GIS, pandapower Electrical Analysis, Deterministic Candidate PNC Generation (SURGE-PY-017), Python Engine MVP Status Baseline, Pandapower Validation (SURGE-PY-015), Python Engine Declared Dependencies (+9 more)

### Community 47 - "Web Map Redesign Plan"
Cohesion: 0.15
Nodes (16): Flow-to-Component Traceability Matrix, App Shell (TopBar, RailNav, SidePanel, MapArea), Web Map Frontend Redesign Implementation Plan, Radix-Based UI Primitives, Vite /api Dev Proxy, web-map-next Application, CSS Custom Property Design Tokens, Web Map Frontend Redesign Design Spec (+8 more)

### Community 48 - "Optimise API Contract Tests"
Cohesion: 0.21
Nodes (15): constraint_v1_payload(), Any, BaseGeometry, fixture, Costs only exist when the caller asks for them, and V1 could not ask.…, Absent rates must read as absent, not as zero. A run with no catalogue has no…, A cost catalogue that misses a conductor must say so. Conductor rates are keyed…, _route_geometry() (+7 more)

### Community 49 - "Pole Deduplication Tests"
Cohesion: 0.33
Nodes (15): _config(), _deduplicate(), _route(), test_aggregate_counts_use_physical_poles_and_retain_route_spans(), test_coincident_unrelated_terminals_are_not_merged(), test_deduplication_is_deterministic_and_order_independent(), test_distinct_terminals_are_not_merged(), test_nearby_mid_route_poles_are_not_merged() (+7 more)

### Community 50 - "ADR-007 Load Flow Validation"
Cohesion: 0.19
Nodes (15): AC Load Flow Validation Module, Deterministic Pandapower Network Builder, Validator-Only Pipeline Position, LoadFlowCableType, LoadFlowConfig, WTGOperatingPoint, ADR-007: Pandapower AC Load Flow Validation, Deterministic Domain-to-Index Mappings (+7 more)

### Community 51 - "Constraint Routing Gap Plan"
Cohesion: 0.13
Nodes (15): avoidance_geojson Request Field, Constraint-aware Routing, constraint_demo_project_v2.json Fixture, Fixture Provenance Vocabulary, spatial_constraint_summary, SURGE-PY-021, Consumption Gap Ticket Plan, data_provenance Column (VERIFIED/INDICATIVE/UNKNOWN) (+7 more)

### Community 52 - "CRS Transformation"
Cohesion: 0.24
Nodes (12): get_transformer(), get_utm_crs(), BaseGeometry, CRS, Get the appropriate UTM CRS for a given longitude and latitude. This is…, Get a PyProj Transformer from src_crs to dst_crs. always_xy=True ensures…, Transform a Shapely geometry using the given transformer., transform_geometry() (+4 more)

### Community 53 - "Land Acquisition Routing Docs"
Cohesion: 0.17
Nodes (13): ConstraintLayer, Order-Independent Deterministic Rasterization, Endpoint Coverage Validation, HARD_EXCLUSION Routing Mode, SOFT_PENALTY Routing Mode, Absence of Elevation/DEM Data, Instrument for Outcome Data, ML Belongs in Prediction, Not the Buy-versus-Span Decision (+5 more)

### Community 54 - "MVP Gap Closure Tickets"
Cohesion: 0.15
Nodes (13): A Fallback Surviving Beside Real Data Is Indistinguishable From It, C-1 Parse and Persist Python Cost, C-2 Real CAPEX in BOM Panel, F-1 Remove length x $80 Cost Fallback, F-2 Remove Frontend Fallbacks, Admin User Panel, Audit Log Coverage, Finding B: Every Project/Job Endpoint Is Unauthenticated (+5 more)

### Community 55 - "CI Gates & Spec Alignment"
Cohesion: 0.17
Nodes (13): Five Evaluation Axes, MVP Definition of Done, Cutover (Docker, CI, README), Manual QA Only Verification, Build-Alongside Migration Plan, CI Quality Gates, Golden Demonstration Dataset, CandidateMetrics Optional Attribute Access (+5 more)

### Community 56 - "Engine Stack & Topology Docs"
Cohesion: 0.17
Nodes (12): Preliminary Topology Indicator, Dark Theme Only This Pass, Migration Global Constraints, No Backend or Database Changes, FastAPI, Euclidean MST Limitation, Python Optimisation Engine, Coincident Endpoint Rejection (+4 more)

### Community 57 - "Engine Architecture Docs"
Cohesion: 0.20
Nodes (12): PNC Network Assembly, Zero Algorithm Duplication in the Orchestrator, app.pnc Orchestration Package, CostSurface Abstraction, SURGE-PY-006 Per-Feeder Minimum Spanning Tree, SURGE-PY-007 Uniform Cost Surface, SURGE-PY-008 A* Physical Routing, SURGE-PY-009 Route Geometry Refinement (+4 more)

### Community 58 - "PNC Assembly Boundary Docs"
Cohesion: 0.17
Nodes (12): Deterministic Feeder and Segment ID Scheme, PNC Assembly Fail-Loud Failure Model, MST Graph as Authoritative Topology, ProjectPNCNetwork, build_project_result(), Fail on Reconciliation Errors, Stable GeoJSON Feature Contract, ProjectOptimizationResult (+4 more)

### Community 59 - "Engine Integration Plan"
Cohesion: 0.17
Nodes (12): PY-034 Land Parcel and Landowner Decision Intelligence, A1 Emit Per-Segment Cable Sizing, A2 Emit the Land Decision, Not Just the Count, A3 Make Micro-Siting Reachable, A4 Expose the Engineering Report, E1 Extend the Parcel Model, PY-030 Per-Segment Cable Sizing, PY-035 Pole Micro-Siting (+4 more)

### Community 60 - "Load Flow Convergence Tests"
Cohesion: 0.32
Nodes (11): Execute AC load flow and map results back to domain models., run_load_flow(), patch, PNCFixture, Tests for AC load flow execution and analysis., Test that a solver failure is caught and handled gracefully., test_cable_overload_violation(), test_non_convergence_graceful() (+3 more)

### Community 61 - "GeoJSON Parsing"
Cohesion: 0.30
Nodes (9): parse_geojson(), Any, BaseGeometry, Serialize a Shapely geometry back into a GeoJSON geometry dictionary., Parse a GeoJSON dictionary (Feature or Geometry) into a Shapely geometry. If…, serialize_geometry(), test_parse_geojson_feature(), test_parse_geojson_geometry_only() (+1 more)

### Community 62 - "Lifecycle Cost Tests"
Cohesion: 0.26
Nodes (9): PNCScenario, One candidate PNC network produced by the scenario generator. Structural…, dummy_electrical_config(), dummy_engineering_assessment(), dummy_lifecycle_config(), dummy_load_flow_result(), dummy_scenario(), fixture (+1 more)

### Community 63 - "Explainability & ML Ranking"
Cohesion: 0.20
Nodes (11): Explainability Touchpoint, Screen 5 — Scenario Comparison, Correctness and Safety Requirement, Explainability, ML Ranking Experimental Labeling, Multi-Objective Optimization, Scenario Comparison Modal, One-Issue-Per-Branch Agent Policy (+3 more)

### Community 64 - "SURGE Ticket Plan Docs"
Cohesion: 0.24
Nodes (11): KmzGeoJsonConverter, Surge MVP Ticket Plan, SURGE-PY-021 V1 Constraint Regression Coverage, SURGE-PY-022 Constraint Fixture Provenance Labeling, SURGE-PY-024 Pole Placement Integration into the Optimisation Workflow, SURGE-PY-025 Pole GeoJSON + API Presentation, SURGE - Smart Utility Routing and Grid Evacuation, SURGE Product Vision (+3 more)

### Community 65 - "V2 Schema Validators"
Cohesion: 0.29
Nodes (4): model_validator, EngineeringScoringWeightsRequest, test_unified_policy_rejects_nonzero_subweights_for_inactive_group(), Self

### Community 66 - "Pole Placement Micro Tests"
Cohesion: 0.18
Nodes (9): PoleMicroSitingConfig, Configuration for deterministic local pole micro-siting. Attributes ----------…, Raise ValueError if *value* is NaN or infinite., _require_finite(), base_config(), pole_config(), fixture, parametrize (+1 more)

### Community 67 - "TRD Pipeline Contracts"
Cohesion: 0.20
Nodes (10): Data Provenance Through the Flow, Cost Surface Not Wired Into Pipeline, Current Implemented Pipeline, Normalized and Sorted Edge Selection, Feeder-Identity Contract Gap, Java RouteService, Per-Feeder MST Topology, Unified UTM Projection Boundary (+2 more)

### Community 68 - "Corpus Provenance & Scenarios"
Cohesion: 0.22
Nodes (10): Screen 3 — Optimisation Settings, Balanced Scenario, com.power.surge.service.classification.AssetClassifier, classify.ts Port, Java AssetClassificationRules, classify.js Imported Unchanged, POST /api/v1/optimise Contract, Java OptimizationJobService (+2 more)

### Community 69 - "Scoring Gap Findings"
Cohesion: 0.22
Nodes (10): Voltage Operating Margin, Cost-Aware Combined Benefit Policy, Deterministic Tie-Breaking Order, Min-Max Benefit Normalization, Four Canonical Objective Groups, Finding A: The Four Scenarios Do Nothing, Routing-Cost Bias Instead of a Fifth Scoring Metric, ScenarioProfile (+2 more)

### Community 70 - "Land CAPEX & Pole Costs"
Cohesion: 0.20
Nodes (10): Pole CAPEX, Missing Stable owner_id, Owner Interaction Count Objective, Pole Micro-Siting (PY-035), A* Candidate Routing, Capacity-Constrained WTG Clustering, MST Radial Feeder Topology, SURGE-PY-010 Pole Placement (+2 more)

### Community 71 - "Scenario Structural Integrity"
Cohesion: 0.31
Nodes (4): Complete result of one ``generate_pnc_scenarios`` call. Attributes ----------…, ScenarioGenerationResult, Every candidate satisfies PY-014 network integrity requirements., TestStructuralIntegrity

### Community 72 - "Report Renderers"
Cohesion: 0.44
Nodes (5): ABC, Render an EngineeringReport to a string format., ReportRenderer, TextRenderer, EngineeringReport

### Community 73 - "Screen Flow & Sync Docs"
Cohesion: 0.22
Nodes (9): Screen 4 — Network Results (Map), Synchronous vs Asynchronous Optimisation, MapCanvas Component, TanStack Query Hooks (lib/query), useUiStore (Zustand UI State), Leaflet Stays Vanilla, Wrapped Not Ported, SurgeMapEngine, TanStack Query for Server State (+1 more)

### Community 74 - "Java/Python Boundary Docs"
Cohesion: 0.25
Nodes (9): Python Presentation Boundary, Python Engine Architecture and GIS Processing, Deferred Java-Level Feeder Aggregation, Stateless FastAPI Optimisation Pipeline, Java/Python Responsibility Split, C-07 Synthetic Elevation Profile Without Disclaimer, Missing Java Constraint and Pole Transport, Failure Must Never Appear as Simulated Success (+1 more)

### Community 75 - "Route Scoring Architecture Docs"
Cohesion: 0.22
Nodes (9): SURGE-PY-011 ROW Corridor and Constraint Analysis, Route Scoring Architecture, Hard-Violation Candidates Excluded from Normalization, Deterministic Min-Max Cohort Normalization, SURGE-PY-012 Preliminary Route Scoring Engine, Explainability, Route, ROW Corridor (+1 more)

### Community 76 - "KMZ Asset Classification"
Cohesion: 0.22
Nodes (9): SURGE-JV-006 KMZ Asset Classification Plan, AssetClassifier, AssetType Domain Enum, evacuation_towers Table, SURGE-JV-006 Ticket, Optimiser Isolation of Non-Optimisable Assets, Preview-Then-Commit Import Flow, Shared Classification Rules in Browser and Backend (+1 more)

### Community 77 - "UX Improvement Report"
Cohesion: 0.25
Nodes (9): AssetClassificationRules, No False-Success in the Demo Path, Two-Day Demo Productisation Sprint, SURGE Frontend UX Improvement Report, Cross-Cutting Accessibility Gaps, C-02 No URL Routing, Phase 1 - Trust and Reliability Roadmap, C-05 Silent API Error Fallbacks (+1 more)

### Community 78 - "PRD Routing Requirements"
Cohesion: 0.22
Nodes (9): Route, ROW Corridor, Topology, cost_function.py Placeholder, NetworkX + Custom A* Routing, Target Full Pipeline, Compatible API / End-to-End Integration (PY-020), Pipeline Orchestration (PY-019) (+1 more)

### Community 79 - "API v2 Endpoints"
Cohesion: 0.36
Nodes (8): post, Execute the complete end-to-end Surge optimisation workflow., run_optimisation(), Explicitly map the API request to Surge domain models., to_workflow_invocation(), OptimiseProjectRequest, test_v2_maps_land_commercial_context(), test_training_corpus_emission_exercises_override_and_labels()

### Community 80 - "GIS Preprocessing"
Cohesion: 0.28
Nodes (7): _extract_features(), Any, Point, Picks the substation feeders should connect to when more than one is supplied.…, _select_primary_substation(), _validate_capacity(), _validate_point_coords()

### Community 81 - "Demo Data & Transparency"
Cohesion: 0.25
Nodes (8): Demo-Data Fallback Behavior, Screen 6 — Reports, Minimum Cost Scenario, Transparency of Maturity, useAuthStore (Zustand Auth State), surge_jwt_token localStorage Key, Typed API Client (lib/api), KMZ Round-Trip Provenance Gap

### Community 82 - "PRD Domain Glossary"
Cohesion: 0.29
Nodes (8): SURGE Application Flow (APP-FLOW), High-Level User Journey, Screen 2 — GIS Layers, Collector Network, Feeder, SURGE Platform, Target Lifecycle Coverage, SURGE Technical Requirements (TRD)

### Community 83 - "Land Acquisition Consumption Gap"
Cohesion: 0.25
Nodes (8): Half-Filled Catalogue Is Worse Than None, L-1 Parse candidates[].land in Java API, L-2 Parcel Decision Table, Sophisticated Engine Fed Bad Data Produces Sophisticated Zeroes, Land Acquisition and Route Decision Engine Analysis, LandTransactionMode (PURCHASE/LEASE/EASEMENT), ParcelCommercialProfile, Present-Value Transaction Option Selection

### Community 84 - "Gap Closure Cost Findings"
Cohesion: 0.29
Nodes (8): L-3 Converge Two Right-of-Way Implementations, Land CAPEX, BOM Electrical Losses Heuristic Bug, Parcel ROW Area Uses Full Polygon Bug, Tier 3: Fix the Two Data-Correctness Bugs, Two Implementations of One Right-of-Way Quantity, ROW Corridor and Parcel Compensation Analysis, SURGE-PY-011 ROW Analysis

### Community 85 - "Integration & Ticket Plan Docs"
Cohesion: 0.25
Nodes (8): B1 Repoint PythonOptimizationClient at /api/v2/optimise, PY-031 Electrical Repair Log, Track B - Move Java to v2, Track C - Java Consumes and Persists, Track D - Surfacing, Additive V1 API Compatibility Contract, MVP Numbering Freeze at SURGE-PY-020, Explicit Post-MVP Work

### Community 86 - "Synthetic Corpus Provenance"
Cohesion: 0.32
Nodes (8): constraint_demo_project_v2.json Contract Fixture, DERIVED Provenance Label, Provenance Vocabulary, PYTHON_CONTRACT_VERIFIED Label, REAL_SOURCE Provenance Label, SYNTHETIC Provenance Label, V1 Legacy Request Adapter, Corpus Generation Fixtures

### Community 87 - "Scenario Variation Tests"
Cohesion: 0.21
Nodes (4): Scenario IDs must be sequential based on accepted candidates, not on the…, Verify parameters are passed into algorithm boundaries, not applied post-hoc., TestScenarioIdsStableOnRejection, TestVariationReachesAlgorithms

### Community 88 - "Cost Model Catalogue Docs"
Cohesion: 0.33
Nodes (7): C-3 Lifecycle Cost Breakdown, C-4 Detailed BoQ Line-Item Table, P-1 Cost Catalogue, Inline Versioned Catalogue Contract, Conductor CAPEX, Catalogue and Lifecycle Currency Must Match, Lifecycle Cost Objective Model

### Community 89 - "GIS Geometry Validation"
Cohesion: 0.43
Nodes (5): BaseGeometry, Validates a shapely geometry. If it's invalid (e.g., self-intersecting…, validate_geometry(), test_validate_invalid_geometry(), test_validate_valid_geometry()

### Community 90 - "Scenario Determinism Tests"
Cohesion: 0.29
Nodes (3): Two runs with identical inputs produce identical structural results., Shuffling turbine input order must not affect the output., TestDeterminism

### Community 92 - "Duplicate Suppression Tests"
Cohesion: 0.40
Nodes (3): Duplicate topologies are recorded as DUPLICATE_TOPOLOGY, not accepted., Force a project so small only one grouping is possible. All non-baseline…, TestDuplicateSuppression

### Community 93 - "Candidate PNC Scenario Docs"
Cohesion: 0.50
Nodes (4): Deterministic Parameter Personalities, Duplicate Topology Suppression, generate_pnc_scenarios(), ScenarioGenerationConfig

### Community 94 - "Consumption Gap Phases"
Cohesion: 0.50
Nodes (4): E-1b Persist Repair Diagnostics, E-3 Per-Feeder Electrical Breakdown, E-4 Diagnostics Panel for Failed Runs, E-6 Repair Exhaustion Reason

### Community 95 - "Pole Micro-Siting Helpers"
Cohesion: 0.50
Nodes (3): PoleMoveScore, Detailed evidence of why a candidate position was evaluated., Ranking: 1. lower owner burden 2. lower parcel burden 3. better span quality 4.…

### Community 96 - "PNC Assembly Reverse Mapping"
Cohesion: 0.50
Nodes (4): Any, LineString, Return a new LineString with coordinate order reversed., _reverse_linestring()

### Community 97 - "MVP Gap Closure Findings"
Cohesion: 0.67
Nodes (3): Announce Results Only After Commit, Asynchronous Job Execution, StaleJobSweeper

### Community 98 - "PNC Assembly BFS"
Cohesion: 0.67
Nodes (3): _bfs_ordered_nodes(), Graph, Return a deterministic BFS traversal from *substation_id*. Neighbours are…

## Ambiguous Edges - Review These
- `Minimum Cost Scenario` → `Typed API Client (lib/api)`  [AMBIGUOUS]
  docs/superpowers/plans/2026-08-12-web-map-frontend-redesign.md · relation: references
- `Absence of Elevation/DEM Data` → `Weighted GIS Cost Surface`  [AMBIGUOUS]
  docs/artifacts/Land Acquisition and Route Decision Engine.md · relation: conceptually_related_to
- `ProjectPNCNetwork` → `Sunday KMZ-to-33 kV Network Delivery Plan`  [AMBIGUOUS]
  docs/artifacts/whats-next.md · relation: references

## Knowledge Gaps
- **89 isolated node(s):** `SyntheticProjectSpec`, `Surge MVP Ticket Plan`, `Compatible API / End-to-End Integration (PY-020)`, `Untyped Test Functions (no-untyped-def)`, `SYN-1-CLUSTERED-8 Fixture` (+84 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 638 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Minimum Cost Scenario` and `Typed API Client (lib/api)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Absence of Elevation/DEM Data` and `Weighted GIS Cost Surface`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `ProjectPNCNetwork` and `Sunday KMZ-to-33 kV Network Delivery Plan`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `ProjectSpatialData` connect `PNC Assembly Tests` to `Candidate Generation Tests`, `Cost Surface`, `WTG Grouping & Topology Search`, `Orchestrator & Search Cache`, `Scenario Config Validation`, `Feeder Validation & Voltage Drop`, `Scenario Models & PNC Errors`, `Scenario Strategy Tests`, `Candidate Diversity Tests`, `Scenario Determinism Tests`, `GIS Preprocessing Tests`, `PNC Assembly & Route Graph`, `GIS Preprocessing`, `Physical Routing Feasibility`, `Route Graph Scenario Tests`, `Scenario Variation Tests`, `GIS Constraint Application`, `Feeder Validation Tests`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `CostSurface` connect `PNC Assembly Tests` to `Candidate Generation Tests`, `Cost Surface`, `WTG Grouping & Topology Search`, `Orchestrator & Search Cache`, `Scenario Models & PNC Errors`, `Route Refinement`, `Constraint Layer Validation`, `A-Star Pathfinding`, `PNC Assembly & Route Graph`, `GIS Preprocessing`, `Physical Routing Feasibility`, `Route Graph Scenario Tests`, `GIS Constraint Application`, `Presentation GeoJSON`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `build_pnc_network()` connect `PNC Assembly Tests` to `WTG Grouping & Topology Search`, `PNC Assembly BFS`, `Scenario Models & PNC Errors`, `Route Refinement`, `Load Flow Execution`, `PNC Assembly & Route Graph`, `Physical Routing Feasibility`, `Route Graph Scenario Tests`, `Engine Architecture Docs`, `PNC Assembly Boundary Docs`, `Presentation GeoJSON`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `ProjectSpatialData` (e.g. with `build_project_graph()` and `group_wtgs()`) actually correct?**
  _`ProjectSpatialData` has 56 INFERRED edges - model-reasoned connections that need verification._