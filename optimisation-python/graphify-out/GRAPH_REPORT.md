# Graph Report - optimisation-python  (2026-09-13)

## Corpus Check
- 193 files · ~101,944 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2061 nodes · 7389 edges · 98 communities (62 shown, 22 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1036 edges (avg confidence: 0.95)
- Semantic token usage: unavailable from the desktop subagent API; no paid API calls.

## Community Hubs (Navigation)
- Candidate Search and Scoring
- Geospatial Data Processing
- Regression Test Coverage
- Routing and Graph Algorithms
- Lifecycle Cost Evaluation
- Regression Test Coverage
- Candidate Search and Scoring
- Regression Test Coverage
- Regression Test Coverage
- Candidate Search and Scoring
- Routing and Graph Algorithms
- Electrical Network Validation
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Land Corridor Analysis
- Regression Test Coverage
- Candidate Search and Scoring
- Regression Test Coverage
- Electrical Network Validation
- Request and Response Schemas
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Candidate Search and Scoring
- Regression Test Coverage
- Electrical Network Validation
- Geospatial Data Processing
- Candidate Search and Scoring
- Regression Test Coverage
- Python Libraries and Utilities
- Routing and Graph Algorithms
- Geospatial Data Processing
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Candidate Search and Scoring
- PNC Network Assembly
- Request and Response Schemas
- Geospatial Data Processing
- Python Libraries and Utilities
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Request and Response Schemas
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- API Request Handling
- Candidate Search and Scoring
- Regression Test Coverage
- Python Libraries and Utilities
- Geospatial Data Processing
- Request and Response Schemas
- Regression Test Coverage
- Python Libraries and Utilities
- Geospatial Data Processing
- Regression Test Coverage
- Regression Test Coverage
- Python Libraries and Utilities
- Python Libraries and Utilities
- Routing and Graph Algorithms
- Routing and Graph Algorithms
- API Request Handling
- Python Libraries and Utilities
- Lifecycle Cost Evaluation
- Python Libraries and Utilities
- Land Corridor Analysis
- Python Libraries and Utilities
- Request and Response Schemas
- Python Libraries and Utilities
- Python Libraries and Utilities
- Python Libraries and Utilities
- Python Libraries and Utilities
- Regression Test Coverage
- Python Libraries and Utilities
- Python Libraries and Utilities
- Python Libraries and Utilities
- Python Libraries and Utilities
- Python Libraries and Utilities
- Regression Test Coverage
- Regression Test Coverage

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
- `Exact Dependency Versions` --semantically_similar_to--> `Exact Dependency Versions`  [INFERRED] [semantically similar]
  requirements.lock.txt → requirements.txt
- `test_route_not_found_raises_domain_error()` --uses--> `RouteNotFoundError`  [INFERRED]
  tests/test_physical_routing.py → app/algorithms/physical_routing.py
- `TestEarlyDuplicateSuppression` --uses--> `PhysicalRoutingResult`  [INFERRED]
  tests/test_scenarios.py → app/algorithms/physical_routing.py
- `TestFailureRecorded` --uses--> `PhysicalRoutingResult`  [INFERRED]
  tests/test_scenarios.py → app/algorithms/physical_routing.py
- `_base_config()` --uses--> `PolePlacementConfig`  [INFERRED]
  tests/test_candidate_evaluation_defects.py → app/algorithms/pole_placement.py

## Import Cycles
- None detected.

## Communities (98 total, 22 thin omitted)

### Community 0 - "Candidate Search and Scoring"
Cohesion: 0.08
Nodes (88): CandidateLifecycleCost, Re-scores the entire eligible archive and updates their evaluation results., _score_archive(), CandidateEngineeringMetrics, Raw engineering quantities extracted for one PNC candidate., End-to-End Optimisation package for Surge. Public API ----------…, InvalidScenarioConfigError, Exception (+80 more)

### Community 1 - "Geospatial Data Processing"
Cohesion: 0.06
Nodes (80): analyse_row_corridors(), _build_corridor(), _build_corridors(), ConstraintFeature, _count_point_geometries(), _count_road_crossings(), _deduplicate_coordinates(), _intersect_corridor() (+72 more)

### Community 2 - "Regression Test Coverage"
Cohesion: 0.05
Nodes (29): Configuration for deterministic PNC scenario generation. Attributes ----------…, ScenarioGenerationConfig, generate_pnc_scenarios(), Generate a configurable set of deterministic PNC network candidates. If…, _PSD, _make_diverse_project(), fixture, When routing fails for a candidate, the attempt is recorded as ROUTING_FAILED… (+21 more)

### Community 3 - "Routing and Graph Algorithms"
Cohesion: 0.09
Nodes (58): PhysicalRoute, PhysicalRoutingResult, ValueError, Validates that the cost surface is suitable for A* routing., validate_cost_surface(), _axis_breakpoints(), _cells_touching_grid_point(), _coordinate_is_within_surface() (+50 more)

### Community 4 - "Lifecycle Cost Evaluation"
Cohesion: 0.08
Nodes (41): CostCatalogueProvider, JSONCatalogueProvider, Catalogue resolution interface., Resolve a cost catalogue by its identifier. Raises: CostConfigurationError: if…, CostConfigurationError, CostEvaluationFailure, CostEvaluationFailureCode, StrEnum (+33 more)

### Community 5 - "Regression Test Coverage"
Cohesion: 0.10
Nodes (54): CandidateElectricalEvaluationError, Exception, Execution error evaluating an individual candidate network. This indicates a…, Electrical feasibility screening and validation., optimise_project(), Run the complete end-to-end Surge optimisation workflow., Fail-fast validation of inputs before any heavy computation., _validate_input() (+46 more)

### Community 6 - "Candidate Search and Scoring"
Cohesion: 0.08
Nodes (45): ArtifactMetadata, load_artifact(), Any, Path, Pipeline, save_artifact(), ValidationSummary, _canonical_fingerprint() (+37 more)

### Community 7 - "Regression Test Coverage"
Cohesion: 0.09
Nodes (55): calculate_span_count(), place_poles_on_route(), Return the number of spans needed to cover *route_length_m* while respecting…, Place physical pole structures along a single refined feeder route. Parameters…, default_config(), make_route(), tests/test_pole_placement.py Unit tests for SURGE-PY-010 — Pole Placement Along…, Route shorter than min_span_m must still produce exactly two poles. (+47 more)

### Community 8 - "Regression Test Coverage"
Cohesion: 0.10
Nodes (50): GroupingObjective, StrEnum, Controls the feeder-assignment objective used during WTG grouping.…, CandidateSpatialResult, EngineeringMetricFailureCode, ParcelEngineeringExposure, StrEnum, Canonical candidate-level engineering metric domain models. (+42 more)

### Community 9 - "Candidate Search and Scoring"
Cohesion: 0.07
Nodes (34): RouteNotFoundError, materialize_candidate_design(), Graph, Materialize a logical topology into a fully routed PNCScenario., AttemptOutcome, NoValidScenarioError, Complete description of algorithm inputs for one candidate scenario. Every…, Diagnostic record for one generation attempt. Attributes ----------… (+26 more)

### Community 10 - "Routing and Graph Algorithms"
Cohesion: 0.09
Nodes (49): _generate_candidates(), _is_feasible(), _network_objective(), optimize_poles(), _owners_for_parcels(), _parcel_layers_for_point(), PoleMicroSitingContext, PoleMicroSitingMove (+41 more)

### Community 11 - "Electrical Network Validation"
Cohesion: 0.11
Nodes (49): RefinedPhysicalRoute, _build_route_map(), calculate_downstream_active_power_mw(), _edge_key(), _evaluate_feeder(), _evaluate_turbines(), _project_nodes(), CRS (+41 more)

### Community 12 - "Regression Test Coverage"
Cohesion: 0.11
Nodes (48): Pandapower electrical AC load flow solver and analysis., Pandapower-based AC load flow validation module., LoadFlowBusResult, LoadFlowFeederResult, LoadFlowNetworkResult, LoadFlowSegmentResult, LoadFlowViolation, LoadFlowViolationCode (+40 more)

### Community 13 - "Regression Test Coverage"
Cohesion: 0.11
Nodes (21): CostSurface, ProjectSpatialData, build_pnc_network(), Construct and return a ``ProjectPNCNetwork`` from validated inputs. Callers…, Run the complete pipeline and return a validated PNC network. Executes WTG…, cost_surface(), _make_project(), fixture (+13 more)

### Community 14 - "Regression Test Coverage"
Cohesion: 0.13
Nodes (44): CandidateScore, CriterionScore, evaluate_network_candidates(), NetworkCandidateMetrics, NormalizationRange, Score, normalize, and rank comparable network-level route candidates.…, RouteScoringResult, RouteScoringWeights (+36 more)

### Community 15 - "Land Corridor Analysis"
Cohesion: 0.14
Nodes (41): _aggregate_cost_basis(), assess_candidate_land(), _assess_parcel(), assess_transaction_option(), present_value_factor(), Decimal, Deterministic commercial decisions for candidate parcel exposures., Return the ordinary-annuity present-value factor. (+33 more)

### Community 16 - "Regression Test Coverage"
Cohesion: 0.11
Nodes (28): Helper to ensure globally unique string IDs for Substations., substation_node_id(), RefinedRoutingResult, assemble_pnc_network(), Validate pre-computed topology and routes, then assemble a PNC network. No…, Exhaustively validate topology ↔ route correspondence before assembly. Checks…, _validate_precomputed_routes(), PNCAssemblyError (+20 more)

### Community 17 - "Candidate Search and Scoring"
Cohesion: 0.10
Nodes (45): CandidateWorkflowResult, WorkflowStage, _active_loss(), _build_comparisons(), _build_economics_summary(), _build_electrical_summary(), _build_land_summary(), _build_physical_summary() (+37 more)

### Community 18 - "Regression Test Coverage"
Cohesion: 0.10
Nodes (42): Execute AC load flow and map results back to domain models., run_load_flow(), Pandapower electrical network builder for AC load flow., Strict input validation prior to network construction. Raises ValueError on any…, _validate_inputs(), LoadFlowConfig, Overall AC load flow configuration for a project simulation. Includes global…, Explicit operating point for a Wind Turbine Generator. Active and reactive… (+34 more)

### Community 19 - "Electrical Network Validation"
Cohesion: 0.10
Nodes (36): _aggregate_downstream_power(), _edge_key(), NoFeasibleCableError, DiGraph, EdgeKey, Exception, Deterministic per-segment cable sizing., Raised when no catalogue cable can carry the required current. (+28 more)

### Community 20 - "Request and Response Schemas"
Cohesion: 0.13
Nodes (39): ProjectOptimizationResult, Map domain workflow results securely back to API boundaries., Expose the per-parcel land decisions, not only the totals., to_api_response(), _to_land_summary(), ApiModel, CableConfigRequest, CandidateCostSummary (+31 more)

### Community 21 - "Regression Test Coverage"
Cohesion: 0.12
Nodes (31): CableSizingResult, build_pandapower_network(), Build a pandapower electrical network from a PNC network. Validates inputs…, network_to_feature_collection(), Any, CRS, Convert a ``ProjectPNCNetwork`` to a GeoJSON FeatureCollection. Parameters…, PNCFeeder (+23 more)

### Community 22 - "Regression Test Coverage"
Cohesion: 0.18
Nodes (29): Helper to ensure globally unique string IDs for WTGs., turbine_node_id(), build_feeder_mst(), Graph, Builds a radial minimum spanning tree (MST) for each feeder group assigned in…, FeederAssignment, FeederGroupingResult, Safe structural validation of candidate topologies. (+21 more)

### Community 23 - "Regression Test Coverage"
Cohesion: 0.16
Nodes (32): ClosedLoopRepairResult, StrEnum, RepairAction, RepairReason, RepairStatus, _describe_exhaustion_reason(), _describe_repair_failure(), _effective_ampacity_a() (+24 more)

### Community 24 - "Candidate Search and Scoring"
Cohesion: 0.12
Nodes (20): evaluate_candidate(), Evaluate one candidate's electrical, engineering, and lifecycle results., CandidateEngineeringAssessment, EngineeringMetricFailure, Complete metrics or explicit extraction failures for one candidate., One deterministic extraction diagnostic for a candidate., PNCScenario, Domain models for SURGE-PY-017 candidate PNC scenario generation. All models… (+12 more)

### Community 25 - "Regression Test Coverage"
Cohesion: 0.23
Nodes (31): group_wtgs(), Uses scipy.optimize.milp to solve the capacitated assignment problem.…, Solve the capacitated assignment problem with an explicit balance objective.…, Deterministically groups wind turbines into feeders such that no feeder exceeds…, _solve_milp_assignment(), _solve_milp_balance(), WindTurbine, _make_project() (+23 more)

### Community 26 - "Electrical Network Validation"
Cohesion: 0.13
Nodes (25): _require_finite_number(), SegmentImpedance, VoltageChangeResult, calculate_segment_impedance(), calculate_three_phase_current_a(), calculate_voltage_change(), Pure balanced three-phase electrical screening primitives., Return nominal-voltage line current for balanced three-phase power. (+17 more)

### Community 27 - "Geospatial Data Processing"
Cohesion: 0.16
Nodes (27): apply_avoidance_constraints(), apply_constraint_layers(), ConstraintLayer, ConstraintMode, ConstraintType, effective_constraint_geometry(), StrEnum, Return the buffered geometry used by routing and compliance checks. (+19 more)

### Community 28 - "Candidate Search and Scoring"
Cohesion: 0.17
Nodes (20): CandidateSearchResult, Evidence from the search process., Backward-compatible alias for the proposal count., Backward-compatible alias for duplicate proposals., Count candidates served by evaluation or exact cache reuse., Backward-compatible alias for failed search candidates., OptimisationWorkflowResult, build_decision_report() (+12 more)

### Community 29 - "Regression Test Coverage"
Cohesion: 0.14
Nodes (23): CandidateSearchStatistics, StrEnum, Base class for search mutations., Statistics for the candidate search process., SearchMutation, SearchTerminationReason, AlternativeSummary, CandidateReference (+15 more)

### Community 30 - "Python Libraries and Utilities"
Cohesion: 0.31
Nodes (16): DecisionReport, build_engineering_report(), Builds the final engineering report sections from a DecisionReport., build_alternatives(), build_economics(), build_electrical(), build_executive_summary(), build_land() (+8 more)

### Community 31 - "Routing and Graph Algorithms"
Cohesion: 0.13
Nodes (22): _can_join_endpoint_cluster(), _classify_pole(), _deduplicate_distances(), deduplicate_pole_endpoints(), _deflection_angle_deg(), _endpoint_pole_records(), _EndpointPoleRecord, _physical_pole_from_endpoint_cluster() (+14 more)

### Community 32 - "Geospatial Data Processing"
Cohesion: 0.15
Nodes (19): get_transformer(), get_utm_crs(), BaseGeometry, CRS, Get the appropriate UTM CRS for a given longitude and latitude. This is…, Get a PyProj Transformer from src_crs to dst_crs. always_xy=True ensures…, Transform a Shapely geometry using the given transformer., transform_geometry() (+11 more)

### Community 33 - "Regression Test Coverage"
Cohesion: 0.20
Nodes (23): Which of the loop's dead ends ended the repair. ``REPAIR_EXHAUSTED`` is…, RepairExhaustionReason, _config(), _invalid_result(), _network(), MonkeyPatch, Which dead end ended the repair. ``REPAIR_EXHAUSTED`` is returned from eight…, Voltage rise is the case where a bigger conductor is not the lever. The… (+15 more)

### Community 34 - "Regression Test Coverage"
Cohesion: 0.16
Nodes (22): OptimiseProjectResponse, _costing_config(), mvp_v2_payload(), fixture, JsonObject, MonkeyPatch, parametrize, The land engine's conclusions have to leave the process. Only… (+14 more)

### Community 35 - "Regression Test Coverage"
Cohesion: 0.25
Nodes (22): Graph, Translates electrical MST edges into physical LineString paths using A* across…, route_collector_topology(), CollectorTopologyResult, FeederTopology, mock_surface(), fixture, test_every_mst_edge_gets_one_route() (+14 more)

### Community 36 - "Regression Test Coverage"
Cohesion: 0.16
Nodes (22): build_project_cost_surface(), grid_to_world(), Convert geographic (projected) coordinates (x, y) to grid cell indices (row,…, Convert grid cell indices (row, col) to the centre of the cell in world…, Creates a CostSurface covering the full project extent (WTGs + Substation)., world_to_grid(), mock_project(), fixture (+14 more)

### Community 37 - "Regression Test Coverage"
Cohesion: 0.09
Nodes (14): _make_project(), Scenario IDs must be sequential based on accepted candidates, not on the…, Build a small ProjectSpatialData. Substation at (sub_x, sub_y)., Duplicate topologies are recorded as DUPLICATE_TOPOLOGY, not accepted., Force a project so small only one grouping is possible. All non-baseline…, Block A* by making every cell impassable except at corners., Two networks with different WTG memberships must have different fingerprints., For a project with only one feasible topology, A* should be called only once,… (+6 more)

### Community 38 - "Candidate Search and Scoring"
Cohesion: 0.25
Nodes (20): _apply_grouping_mutation(), _apply_topology_mutation(), _compute_mutation_features(), _extract_design(), _generate_reassignment_mutations(), _generate_reconnect_mutations(), _generate_swap_mutations(), _get_turbine() (+12 more)

### Community 39 - "PNC Network Assembly"
Cohesion: 0.13
Nodes (20): _bfs_ordered_nodes(), _build_pnc_network(), _build_route_lookup(), _collect_wtg_coordinates(), _feeder_suffix(), _normalise_feeder_id(), Any, Graph (+12 more)

### Community 40 - "Request and Response Schemas"
Cohesion: 0.19
Nodes (17): post, Execute the complete end-to-end Surge optimisation workflow., run_optimisation(), _compatibility_cable_config(), _legacy_message(), legacy_to_workflow_invocation(), Derive the cable ampacity needed to retain the legacy feeder-capacity input., Map the Java-compatible V1 request into the canonical workflow input. (+9 more)

### Community 41 - "Geospatial Data Processing"
Cohesion: 0.23
Nodes (18): _as_finite_number(), _constraint_mode(), _constraint_type(), ConstraintApplication, ingest_avoidance_constraints(), _layer_id(), _normalize_token(), _numeric_property() (+10 more)

### Community 42 - "Python Libraries and Utilities"
Cohesion: 0.22
Nodes (15): Exceptions for the presentation boundary layer., Presentation layer for creating map-ready JSON result boundaries., ElectricalSummary, FeederResult, NetworkSummary, PoleSummary, PresentationModel, BaseModel (+7 more)

### Community 43 - "Regression Test Coverage"
Cohesion: 0.20
Nodes (16): a_star(), AStarResult, GridCell, empty_surface(), fixture, test_astar_is_deterministic(), test_corner_cutting_prevented(), test_diagonal_distance_cost() (+8 more)

### Community 44 - "Regression Test Coverage"
Cohesion: 0.20
Nodes (17): build_project_graph(), Graph, Constructs an undirected complete topology graph from project spatial data.…, mock_crs(), CRS, fixture, sample_project(), test_complete_graph_edge_count() (+9 more)

### Community 45 - "Regression Test Coverage"
Cohesion: 0.35
Nodes (17): process_project_data(), Parses WTG and Substation GeoJSON, verifies geometries, calculates a common…, _make_fc(), _make_pt(), Any, test_blank_ids(), test_duplicate_ids(), test_empty_wtg_rejected() (+9 more)

### Community 46 - "Request and Response Schemas"
Cohesion: 0.24
Nodes (14): post, run_optimisation(), _legacy_pole_collection(), _legacy_route_collection(), Any, Build the additive V1 response while preserving its legacy fields., to_legacy_api_response(), ElectricalParams (+6 more)

### Community 47 - "Regression Test Coverage"
Cohesion: 0.21
Nodes (16): create_payload(), Any, The land engine is reached through v1 as well as v2. Java calls v1, and v1 is…, Every existing caller sends no land context and must keep working., test_coincident_route_endpoints_return_422(), test_empty_wtg_collection(), test_invalid_scenario(), test_invalid_wtg_geometry() (+8 more)

### Community 48 - "Regression Test Coverage"
Cohesion: 0.21
Nodes (15): constraint_v1_payload(), Any, BaseGeometry, fixture, Costs only exist when the caller asks for them, and V1 could not ask.…, Absent rates must read as absent, not as zero. A run with no catalogue has no…, A cost catalogue that misses a conductor must say so. Conductor rates are keyed…, _route_geometry() (+7 more)

### Community 49 - "Regression Test Coverage"
Cohesion: 0.33
Nodes (15): _config(), _deduplicate(), _route(), test_aggregate_counts_use_physical_poles_and_retain_route_spans(), test_coincident_unrelated_terminals_are_not_merged(), test_deduplication_is_deterministic_and_order_independent(), test_distinct_terminals_are_not_merged(), test_nearby_mid_route_poles_are_not_merged() (+7 more)

### Community 50 - "API Request Handling"
Cohesion: 0.19
Nodes (7): health_check(), get_settings(), Settings, create_application(), BaseSettings, FastAPI, get

### Community 51 - "Candidate Search and Scoring"
Cohesion: 0.23
Nodes (12): _avoidance_geojson(), _costing_config(), generate_synthetic_projects(), JsonObject, Path, Return deterministic hard and soft routing constraints., SyntheticProjectSpec, build_demo_project_data() (+4 more)

### Community 52 - "Regression Test Coverage"
Cohesion: 0.15
Nodes (13): PolePlacementConfig, Immutable configuration for the pole placement engine. All numeric fields must…, Assert all placement invariants for a completed PoleRouteResult. Raises…, _validate_pole_route_result(), pole_config(), fixture, PolePlacementConfig must reject nonsensical span parameters., Route length 101 m with target 100, min 90, max 120 should produce ONE span of… (+5 more)

### Community 53 - "Python Libraries and Utilities"
Cohesion: 0.35
Nodes (12): build_enriched_geojson(), _enrich_node(), _enrich_segment(), Any, Map-ready WGS-84 GeoJSON enrichment with electrical telemetry., Reject values that cannot be emitted as strict interoperable JSON., Return deterministic WGS-84 PNC features with optional LF telemetry. The PNC…, _require_feature_id() (+4 more)

### Community 54 - "Geospatial Data Processing"
Cohesion: 0.31
Nodes (9): parse_geojson(), Any, BaseGeometry, Serialize a Shapely geometry back into a GeoJSON geometry dictionary., Parse a GeoJSON dictionary (Feature or Geometry) into a Shapely geometry. If…, serialize_geometry(), test_parse_geojson_feature(), test_parse_geojson_geometry_only() (+1 more)

### Community 55 - "Request and Response Schemas"
Cohesion: 0.29
Nodes (4): EngineeringScoringWeightsRequest, model_validator, Self, test_unified_policy_rejects_nonzero_subweights_for_inactive_group()

### Community 56 - "Regression Test Coverage"
Cohesion: 0.31
Nodes (4): Complete result of one ``generate_pnc_scenarios`` call. Attributes ----------…, ScenarioGenerationResult, Every candidate satisfies PY-014 network integrity requirements., TestStructuralIntegrity

### Community 57 - "Python Libraries and Utilities"
Cohesion: 0.44
Nodes (5): ABC, Render an EngineeringReport to a string format., ReportRenderer, TextRenderer, EngineeringReport

### Community 58 - "Geospatial Data Processing"
Cohesion: 0.43
Nodes (5): BaseGeometry, Validates a shapely geometry. If it's invalid (e.g., self-intersecting…, validate_geometry(), test_validate_invalid_geometry(), test_validate_valid_geometry()

### Community 59 - "Regression Test Coverage"
Cohesion: 0.33
Nodes (6): place_poles_on_routes(), Place poles on every refined route and aggregate results. Pole IDs are unique…, Two routes sharing a topology node ID each produce their own terminal pole.…, place_poles_on_routes handles routes from different feeders., test_multiple_feeders_processed(), test_shared_topology_metadata_retained_for_network_deduplication()

### Community 60 - "Regression Test Coverage"
Cohesion: 0.33
Nodes (6): Deterministic Synthetic Corpus Layouts, Electrical Evaluation Variation, Non-Round-Trip Provenance Limit, Provenance Classification Vocabulary, Python Contract Fixture, Spatial Constraint Processing Behavior

### Community 62 - "Python Libraries and Utilities"
Cohesion: 0.67
Nodes (3): Current MVP Routed Network Baseline, Implemented PNC and Validation Modules, Planned Post-MVP ML Ranking and GIS Rasterization

## Knowledge Gaps
- **18 isolated node(s):** `SyntheticProjectSpec`, `Optimisation Python README`, `GIS Optimisation Service Scope`, `Implemented PNC and Validation Modules`, `Planned Post-MVP ML Ranking and GIS Rasterization` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 521 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ProjectSpatialData` connect `Regression Test Coverage` to `Geospatial Data Processing`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `PNC Network Assembly`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Electrical Network Validation`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Geospatial Data Processing`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `CostSurface` connect `Regression Test Coverage` to `Regression Test Coverage`, `Routing and Graph Algorithms`, `Regression Test Coverage`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Geospatial Data Processing`, `Geospatial Data Processing`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Candidate Search and Scoring`, `PNC Network Assembly`, `Geospatial Data Processing`, `Regression Test Coverage`, `Candidate Search and Scoring`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `ProjectPNCNetwork` connect `Regression Test Coverage` to `Candidate Search and Scoring`, `Geospatial Data Processing`, `Regression Test Coverage`, `Lifecycle Cost Evaluation`, `Regression Test Coverage`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Electrical Network Validation`, `Candidate Search and Scoring`, `Routing and Graph Algorithms`, `Geospatial Data Processing`, `Regression Test Coverage`, `PNC Network Assembly`, `Python Libraries and Utilities`, `Regression Test Coverage`, `Python Libraries and Utilities`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `ProjectSpatialData` (e.g. with `build_project_graph()` and `group_wtgs()`) actually correct?**
  _`ProjectSpatialData` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `CostSurface` (e.g. with `a_star()` and `route_collector_topology()`) actually correct?**
  _`CostSurface` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `LoadFlowConfig` (e.g. with `evaluate_candidate_cost()` and `run_load_flow()`) actually correct?**
  _`LoadFlowConfig` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `ProjectPNCNetwork` (e.g. with `place_poles_on_network()` and `size_cables_for_network()`) actually correct?**
  _`ProjectPNCNetwork` has 24 INFERRED edges - model-reasoned connections that need verification._

## Extraction audit

Code was extracted locally through AST parsing. Documents were extracted by session subagents, without a paid API call. Actual semantic input/output token counts are unavailable; numeric zero fields are schema placeholders, not measured usage. Documentation requirements, plans, and dated journal entries are source claims, not proof of implemented behavior.

Graph integrity diagnostics: see GRAPH_HEALTH.md.

Source graph warning: 481 unresolved-endpoint edges were omitted; 1,724 parallel relationships collapse in the simple graph view. Raw extraction is retained in extraction.json. pyproject.toml produced no AST nodes.
