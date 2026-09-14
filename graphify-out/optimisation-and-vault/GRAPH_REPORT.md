# Graph Report - surge  (2026-09-13)

## Corpus Check
- 259 files · ~159,090 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2315 nodes · 8110 edges · 108 communities (68 shown, 26 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 1207 edges (avg confidence: 0.94)
- Semantic token usage: unavailable from the desktop subagent API; no paid API calls.

## Community Hubs (Navigation)
- Regression Test Coverage
- System Architecture
- Candidate Search and Scoring
- Lifecycle Cost Evaluation
- Geospatial Data Processing
- Regression Test Coverage
- Regression Test Coverage
- Routing and Graph Algorithms
- Electrical Network Validation
- Candidate Search and Scoring
- Regression Test Coverage
- Candidate Search and Scoring
- Regression Test Coverage
- Historical Engineering Journal
- Routing and Graph Algorithms
- Electrical Network Validation
- Network Optimisation Design
- Candidate Search and Scoring
- Regression Test Coverage
- PNC Network Assembly
- Land Corridor Analysis
- Regression Test Coverage
- Python Libraries and Utilities
- Python Engine Engineering
- Regression Test Coverage
- Candidate Search and Scoring
- Regression Test Coverage
- Request and Response Schemas
- Regression Test Coverage
- Request and Response Schemas
- Regression Test Coverage
- Regression Test Coverage
- Candidate Search and Scoring
- Regression Test Coverage
- Routing and Graph Algorithms
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Geospatial Data Processing
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- Geospatial Data Processing
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- API Request Handling
- Candidate Search and Scoring
- Candidate Search and Scoring
- Request and Response Schemas
- Geospatial Data Processing
- Regression Test Coverage
- Request and Response Schemas
- Geospatial Data Processing
- Regression Test Coverage
- ADR-003 ML Ranking
- Electrical Network Validation
- Geospatial Data Processing
- Regression Test Coverage
- Regression Test Coverage
- Regression Test Coverage
- 2026-08-16-ark
- Python Libraries and Utilities
- Regression Test Coverage
- Documentation Templates
- Documentation Templates
- Documentation Templates
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
1. `ProjectSpatialData` - 174 edges
2. `CostSurface` - 146 edges
3. `LoadFlowConfig` - 100 edges
4. `ProjectPNCNetwork` - 89 edges
5. `CollectorTopologyResult` - 80 edges
6. `WindTurbine` - 72 edges
7. `LoadFlowNetworkResult` - 65 edges
8. `generate_pnc_scenarios()` - 60 edges
9. `optimise_project()` - 58 edges
10. `LoadFlowCableType` - 54 edges

## Surprising Connections (you probably didn't know these)
- `Multi-Objective Candidate Scoring` --references--> `CandidateLifecycleCost`  [INFERRED]
  obsidian-vault/08-python-engine/Multi-Objective Candidate Scoring.md → optimisation-python/app/costing/models.py
- `Canonical Candidate Engineering Metrics` --references--> `CandidateEngineeringMetrics`  [INFERRED]
  obsidian-vault/08-python-engine/Canonical Candidate Engineering Metrics.md → optimisation-python/app/optimisation/engineering_metric_models.py
- `Multi-Objective Candidate Scoring` --references--> `CandidateEngineeringMetrics`  [INFERRED]
  obsidian-vault/08-python-engine/Multi-Objective Candidate Scoring.md → optimisation-python/app/optimisation/engineering_metric_models.py
- `Python Microservice Overview & Layout` --references--> `CandidateEngineeringMetrics`  [INFERRED]
  obsidian-vault/08-python-engine/Overview & Layout.md → optimisation-python/app/optimisation/engineering_metric_models.py
- `Surge MVP Ticket Plan` --references--> `CandidateEngineeringMetrics`  [INFERRED]
  obsidian-vault/08-python-engine/Surge MVP Ticket Plan.md → optimisation-python/app/optimisation/engineering_metric_models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Implemented feeder optimization pipeline** — obsidian-vault::05_optimization_feeder_planning_end_to_end_pipeline, obsidian-vault::05_optimization_per_feeder_mst_topology_deterministic_radial_mst, obsidian-vault::04_architecture_python_engine_physical_routing_pipeline, obsidian-vault::05_optimization_cost_model_decimal_lifecycle_costing [EXTRACTED 1.00]
- **Implemented SURGE vertical slice architecture** — obsidian-vault::04_architecture_frontend_web_map_next, obsidian-vault::04_architecture_backend_async_optimization_orchestration, obsidian-vault::04_architecture_python_engine_physical_routing_pipeline, obsidian-vault::04_architecture_database_wgs84_spatial_storage [EXTRACTED 1.00]

## Communities (108 total, 26 thin omitted)

### Community 0 - "Regression Test Coverage"
Cohesion: 0.06
Nodes (86): ABC, CandidateWorkflowResult, _active_loss(), _build_comparisons(), build_decision_report(), _build_economics_summary(), _build_electrical_summary(), _build_land_summary() (+78 more)

### Community 1 - "System Architecture"
Cohesion: 0.06
Nodes (84): Implemented four deterministic scenarios, SURGE Master Dashboard, Implemented end-to-end vertical slice MVP, Planned production security hardening backlog, Completed phased backend and frontend workstreams, MVP Execution Plan Frontend and Java, Verified MVP release gate, Implemented versioned Java Python result contract (+76 more)

### Community 2 - "Candidate Search and Scoring"
Cohesion: 0.10
Nodes (73): CandidateEngineeringMetrics, Raw engineering quantities extracted for one PNC candidate., compute_economic_context_id(), compute_normalization_ranges(), evaluate_cohort(), extract_candidate_assessment(), _get_group_weight(), _get_metric_group() (+65 more)

### Community 3 - "Lifecycle Cost Evaluation"
Cohesion: 0.07
Nodes (57): Vision lifecycle cost optimization, Implemented CAPEX and loss OPEX model, Implemented Decimal lifecycle costing, Lifecycle Cost Objective Model SURGE PY 028, Implemented partial cost failure reporting, CAPEX and discounted electrical-loss OPEX, Decimal arithmetic with bankers rounding, ADR-004 Lifecycle Cost Objective document (+49 more)

### Community 4 - "Geospatial Data Processing"
Cohesion: 0.06
Nodes (74): analyse_row_corridors(), _build_corridor(), _build_corridors(), ConstraintFeature, _count_point_geometries(), _count_road_crossings(), _deduplicate_coordinates(), _intersect_corridor() (+66 more)

### Community 5 - "Regression Test Coverage"
Cohesion: 0.07
Nodes (37): Helper to ensure globally unique string IDs for Substations., substation_node_id(), build_project_cost_surface(), grid_to_world(), Convert geographic (projected) coordinates (x, y) to grid cell indices (row,…, Convert grid cell indices (row, col) to the centre of the cell in world…, Creates a CostSurface covering the full project extent (WTGs + Substation)., world_to_grid() (+29 more)

### Community 6 - "Regression Test Coverage"
Cohesion: 0.08
Nodes (63): calculate_span_count(), place_poles_on_route(), place_poles_on_routes(), Return the number of spans needed to cover *route_length_m* while respecting…, Place physical pole structures along a single refined feeder route. Parameters…, Place poles on every refined route and aggregate results. Pole IDs are unique…, default_config(), make_route() (+55 more)

### Community 7 - "Routing and Graph Algorithms"
Cohesion: 0.11
Nodes (58): PhysicalRoute, PhysicalRoutingResult, Validates that the cost surface is suitable for A* routing., validate_cost_surface(), _axis_breakpoints(), _cells_touching_grid_point(), _coordinate_is_within_surface(), _cost_is_not_greater() (+50 more)

### Community 8 - "Electrical Network Validation"
Cohesion: 0.10
Nodes (52): RefinedPhysicalRoute, RefinedRoutingResult, _build_route_map(), calculate_downstream_active_power_mw(), _edge_key(), _evaluate_feeder(), _evaluate_turbines(), _project_nodes() (+44 more)

### Community 9 - "Candidate Search and Scoring"
Cohesion: 0.07
Nodes (43): Candidate attempt diagnostics, Implemented five-personality candidate schedule, Candidate PNC Scenario Generation, Pre-routing topology fingerprinting, GroupingObjective, StrEnum, Controls the feeder-assignment objective used during WTG grouping.…, Safe structural validation of candidate topologies. (+35 more)

### Community 10 - "Regression Test Coverage"
Cohesion: 0.09
Nodes (46): Pandapower electrical AC load flow solver and analysis., build_pandapower_network(), Pandapower electrical network builder for AC load flow., Strict input validation prior to network construction. Raises ValueError on any…, Build a pandapower electrical network from a PNC network. Validates inputs…, _validate_inputs(), LoadFlowConfig, Electrical configuration models for AC load flow. (+38 more)

### Community 11 - "Candidate Search and Scoring"
Cohesion: 0.08
Nodes (45): ArtifactMetadata, load_artifact(), Any, Path, Pipeline, save_artifact(), ValidationSummary, _canonical_fingerprint() (+37 more)

### Community 12 - "Regression Test Coverage"
Cohesion: 0.13
Nodes (50): _compute_electrical_context_id(), optimise_project(), Compute a stable hash representing the electrical evaluation context., Run the complete end-to-end Surge optimisation workflow., Fail-fast validation of inputs before any heavy computation., _validate_input(), compute_evaluation_context_id(), _costing_context() (+42 more)

### Community 13 - "Historical Engineering Journal"
Cohesion: 0.04
Nodes (52): Testing Strategy and Current Status, Documented Java backend verification, Documented multi-tier CI matrix, Documented Python optimizer verification, ADR-002: Use PostGIS for Spatial Persistence, Accepted and implemented PostGIS authoritative store, PostGIS spatial indexing and SQL rationale, WGS84 public geometry and Flyway schema evolution (+44 more)

### Community 14 - "Routing and Graph Algorithms"
Cohesion: 0.09
Nodes (49): _generate_candidates(), _is_feasible(), _network_objective(), optimize_poles(), _owners_for_parcels(), _parcel_layers_for_point(), PoleMicroSitingContext, PoleMicroSitingMove (+41 more)

### Community 15 - "Electrical Network Validation"
Cohesion: 0.08
Nodes (46): _aggregate_downstream_power(), CableSizingResult, _edge_key(), NoFeasibleCableError, DiGraph, EdgeKey, Exception, Deterministic per-segment cable sizing. (+38 more)

### Community 16 - "Network Optimisation Design"
Cohesion: 0.06
Nodes (51): Hard radial topology constraint, Implemented route decision summary, Implemented deterministic engineering ground truth, Implemented candidate disqualification audit, Explainable Engineering Decisions and Audit Trail, Feeder Topology and Physical Network Planning, Implemented end to end feeder planning pipeline, Implemented radial topology invariant (+43 more)

### Community 17 - "Candidate Search and Scoring"
Cohesion: 0.09
Nodes (45): place_poles_on_network(), PolePlacementConfig, Immutable configuration for the pole placement engine. All numeric fields must…, Build the canonical pole network for an assembled project PNC. Pole placement…, effective_constraint_geometry(), Return the buffered geometry used by routing and compliance checks., CandidateSpatialResult, EngineeringMetricFailure (+37 more)

### Community 18 - "Regression Test Coverage"
Cohesion: 0.13
Nodes (44): CandidateScore, CriterionScore, evaluate_network_candidates(), NetworkCandidateMetrics, NormalizationRange, Score, normalize, and rank comparable network-level route candidates.…, RouteScoringResult, RouteScoringWeights (+36 more)

### Community 19 - "PNC Network Assembly"
Cohesion: 0.07
Nodes (37): _bfs_ordered_nodes(), _build_pnc_network(), _build_route_lookup(), _collect_wtg_coordinates(), _feeder_suffix(), _normalise_feeder_id(), Any, Graph (+29 more)

### Community 20 - "Land Corridor Analysis"
Cohesion: 0.14
Nodes (36): _aggregate_cost_basis(), assess_candidate_land(), _assess_parcel(), assess_transaction_option(), present_value_factor(), Decimal, Deterministic commercial decisions for candidate parcel exposures., Return the ordinary-annuity present-value factor. (+28 more)

### Community 21 - "Regression Test Coverage"
Cohesion: 0.10
Nodes (21): assemble_pnc_network(), Validate pre-computed topology and routes, then assemble a PNC network. No…, _make_simple_route(), _make_single_edge_topology(), _make_single_route_result(), _ordered_edge(), LineString, Integration and unit tests for SURGE-PY-014: PNC Network Assembly. Two public… (+13 more)

### Community 22 - "Python Libraries and Utilities"
Cohesion: 0.12
Nodes (34): PresentationDataMismatchError, ValueError, Exceptions for the presentation boundary layer., Raised when there is a mismatch between physical and electrical networks.…, build_enriched_geojson(), _enrich_node(), _enrich_segment(), Any (+26 more)

### Community 23 - "Python Engine Engineering"
Cohesion: 0.09
Nodes (36): Deterministic load-flow grid builder, AC Load Flow Validation, Graceful load-flow non-convergence, Implemented Pandapower Newton-Raphson validation, All-or-nothing metric availability, Implemented canonical candidate metrics, Canonical Candidate Engineering Metrics, Metrics feed scoring and lifecycle costing (+28 more)

### Community 24 - "Regression Test Coverage"
Cohesion: 0.14
Nodes (34): LoadFlowBusResult, LoadFlowFeederResult, LoadFlowNetworkResult, LoadFlowViolation, Complete summary of the electrical analysis for a PNC Network. If `converged`…, An electrical constraint violation or load-flow error., AC load flow result for a single node (bus)., Summary of load flow results across a single feeder. (+26 more)

### Community 25 - "Candidate Search and Scoring"
Cohesion: 0.11
Nodes (26): PNCScenario, One candidate PNC network produced by the scenario generator. Structural…, CandidateEvaluation, OptimizationRecommendation, CandidateSearchResult, CandidateSearchStatistics, StrEnum, Evidence from the search process. (+18 more)

### Community 26 - "Regression Test Coverage"
Cohesion: 0.15
Nodes (34): ClosedLoopRepairResult, StrEnum, RepairAction, RepairReason, RepairStatus, _describe_exhaustion_reason(), _describe_repair_failure(), _effective_ampacity_a() (+26 more)

### Community 27 - "Request and Response Schemas"
Cohesion: 0.15
Nodes (31): Map domain workflow results securely back to API boundaries., Expose the per-parcel land decisions, not only the totals., to_api_response(), _to_land_summary(), ApiModel, CandidateCostSummary, CandidateLandSummary, CandidateSummary (+23 more)

### Community 28 - "Regression Test Coverage"
Cohesion: 0.23
Nodes (31): group_wtgs(), Uses scipy.optimize.milp to solve the capacitated assignment problem.…, Solve the capacitated assignment problem with an explicit balance objective.…, Deterministically groups wind turbines into feeders such that no feeder exceeds…, _solve_milp_assignment(), _solve_milp_balance(), WindTurbine, _make_project() (+23 more)

### Community 29 - "Request and Response Schemas"
Cohesion: 0.15
Nodes (28): post, run_optimisation(), _compatibility_cable_config(), _legacy_message(), _legacy_pole_collection(), _legacy_route_collection(), legacy_to_workflow_invocation(), Any (+20 more)

### Community 30 - "Regression Test Coverage"
Cohesion: 0.17
Nodes (29): Graph, ValueError, Translates electrical MST edges into physical LineString paths using A* across…, route_collector_topology(), RouteNotFoundError, CollectorTopologyResult, FeederTopology, materialize_candidate_design() (+21 more)

### Community 31 - "Regression Test Coverage"
Cohesion: 0.20
Nodes (26): Helper to ensure globally unique string IDs for WTGs., turbine_node_id(), build_feeder_mst(), Graph, Builds a radial minimum spanning tree (MST) for each feeder group assigned in…, FeederAssignment, FeederGroupingResult, Strictly validates hard structural invariants for a candidate. Returns True if… (+18 more)

### Community 32 - "Candidate Search and Scoring"
Cohesion: 0.16
Nodes (28): _apply_grouping_mutation(), _apply_topology_mutation(), _compute_mutation_features(), _extract_design(), _generate_reassignment_mutations(), _generate_reconnect_mutations(), _generate_swap_mutations(), _get_turbine() (+20 more)

### Community 33 - "Regression Test Coverage"
Cohesion: 0.17
Nodes (24): SegmentImpedance, VoltageChangeResult, calculate_segment_impedance(), calculate_three_phase_current_a(), calculate_voltage_change(), Pure balanced three-phase electrical screening primitives., Return nominal-voltage line current for balanced three-phase power., Return series impedance for a route length measured in metres. (+16 more)

### Community 34 - "Routing and Graph Algorithms"
Cohesion: 0.13
Nodes (22): _can_join_endpoint_cluster(), _classify_pole(), _deduplicate_distances(), deduplicate_pole_endpoints(), _deflection_angle_deg(), _endpoint_pole_records(), _EndpointPoleRecord, _physical_pole_from_endpoint_cluster() (+14 more)

### Community 35 - "Regression Test Coverage"
Cohesion: 0.14
Nodes (8): generate_pnc_scenarios(), Generate a configurable set of deterministic PNC network candidates. If…, _PSD, SCN-001, SCN-002, SCN-003 with complete ProjectPNCNetworks., Two identical runs produce identical IDs in identical order., TestConfigurableCandidateCount, TestDefaultCandidateGeneration, TestStableScenarioIds

### Community 36 - "Regression Test Coverage"
Cohesion: 0.20
Nodes (23): Which of the loop's dead ends ended the repair. ``REPAIR_EXHAUSTED`` is…, RepairExhaustionReason, _config(), _invalid_result(), _network(), MonkeyPatch, Which dead end ended the repair. ``REPAIR_EXHAUSTED`` is returned from eight…, Voltage rise is the case where a bigger conductor is not the lever. The… (+15 more)

### Community 37 - "Regression Test Coverage"
Cohesion: 0.19
Nodes (23): apply_avoidance_constraints(), apply_constraint_layers(), ConstraintMode, ConstraintType, StrEnum, Return a copy of ``surface`` with hard blocks and soft costs applied., Compatibility wrapper returning only the rasterized cost surface., Routing treatment applied to one spatial constraint. (+15 more)

### Community 38 - "Regression Test Coverage"
Cohesion: 0.24
Nodes (23): evaluate_candidate(), Evaluate one candidate's electrical, engineering, and lifecycle results., _base_config(), _load_flow_config(), _load_flow_result(), _pole_config_with_micro_siting(), _pole_config_without_micro_siting(), _project_input() (+15 more)

### Community 39 - "Regression Test Coverage"
Cohesion: 0.09
Nodes (14): _make_project(), Scenario IDs must be sequential based on accepted candidates, not on the…, Build a small ProjectSpatialData. Substation at (sub_x, sub_y)., Duplicate topologies are recorded as DUPLICATE_TOPOLOGY, not accepted., Force a project so small only one grouping is possible. All non-baseline…, Block A* by making every cell impassable except at corners., Two networks with different WTG memberships must have different fingerprints., For a project with only one feasible topology, A* should be called only once,… (+6 more)

### Community 40 - "Regression Test Coverage"
Cohesion: 0.17
Nodes (20): OptimiseProjectResponse, _costing_config(), mvp_v2_payload(), fixture, JsonObject, MonkeyPatch, parametrize, The land engine's conclusions have to leave the process. Only… (+12 more)

### Community 41 - "Regression Test Coverage"
Cohesion: 0.12
Nodes (10): _make_diverse_project(), fixture, 12 WTGs spread across the large cost surface in 3 clusters. Designed to allow 3…, For a fixture supporting alternatives, accepted fingerprints differ., For the diverse 12-WTG project, the balanced strategy should produce a feeder…, TestBalancedCandidatesRespectCapacity, TestBalanceStrategyImproves, TestBaseGraphNotMutated (+2 more)

### Community 42 - "Regression Test Coverage"
Cohesion: 0.19
Nodes (18): Execute AC load flow and map results back to domain models., run_load_flow(), LoadFlowViolationCode, StrEnum, Specific codes for electrical violations and solver errors., base_config(), fixture, patch (+10 more)

### Community 43 - "Geospatial Data Processing"
Cohesion: 0.23
Nodes (18): _as_finite_number(), _constraint_mode(), _constraint_type(), ConstraintApplication, ingest_avoidance_constraints(), _layer_id(), _normalize_token(), _numeric_property() (+10 more)

### Community 44 - "Regression Test Coverage"
Cohesion: 0.20
Nodes (16): a_star(), AStarResult, GridCell, empty_surface(), fixture, test_astar_is_deterministic(), test_corner_cutting_prevented(), test_diagonal_distance_cost() (+8 more)

### Community 45 - "Regression Test Coverage"
Cohesion: 0.20
Nodes (17): build_project_graph(), Graph, Constructs an undirected complete topology graph from project spatial data.…, mock_crs(), CRS, fixture, sample_project(), test_complete_graph_edge_count() (+9 more)

### Community 46 - "Regression Test Coverage"
Cohesion: 0.35
Nodes (17): process_project_data(), Parses WTG and Substation GeoJSON, verifies geometries, calculates a common…, _make_fc(), _make_pt(), Any, test_blank_ids(), test_duplicate_ids(), test_empty_wtg_rejected() (+9 more)

### Community 47 - "Regression Test Coverage"
Cohesion: 0.21
Nodes (16): create_payload(), Any, The land engine is reached through v1 as well as v2. Java calls v1, and v1 is…, Every existing caller sends no land context and must keep working., test_coincident_route_endpoints_return_422(), test_empty_wtg_collection(), test_invalid_scenario(), test_invalid_wtg_geometry() (+8 more)

### Community 48 - "Geospatial Data Processing"
Cohesion: 0.24
Nodes (12): get_transformer(), get_utm_crs(), BaseGeometry, CRS, Get the appropriate UTM CRS for a given longitude and latitude. This is…, Get a PyProj Transformer from src_crs to dst_crs. always_xy=True ensures…, Transform a Shapely geometry using the given transformer., transform_geometry() (+4 more)

### Community 49 - "Regression Test Coverage"
Cohesion: 0.19
Nodes (5): Configuration for deterministic PNC scenario generation. Attributes ----------…, ScenarioGenerationConfig, Verify parameters are passed into algorithm boundaries, not applied post-hoc., TestConfigValidation, TestVariationReachesAlgorithms

### Community 50 - "Regression Test Coverage"
Cohesion: 0.21
Nodes (15): constraint_v1_payload(), Any, BaseGeometry, fixture, Costs only exist when the caller asks for them, and V1 could not ask.…, Absent rates must read as absent, not as zero. A run with no catalogue has no…, A cost catalogue that misses a conductor must say so. Conductor rates are keyed…, _route_geometry() (+7 more)

### Community 51 - "Regression Test Coverage"
Cohesion: 0.33
Nodes (15): _config(), _deduplicate(), _route(), test_aggregate_counts_use_physical_poles_and_retain_route_spans(), test_coincident_unrelated_terminals_are_not_merged(), test_deduplication_is_deterministic_and_order_independent(), test_distinct_terminals_are_not_merged(), test_nearby_mid_route_poles_are_not_merged() (+7 more)

### Community 52 - "API Request Handling"
Cohesion: 0.19
Nodes (7): health_check(), get_settings(), Settings, create_application(), BaseSettings, FastAPI, get

### Community 53 - "Candidate Search and Scoring"
Cohesion: 0.23
Nodes (12): _avoidance_geojson(), _costing_config(), generate_synthetic_projects(), JsonObject, Path, Return deterministic hard and soft routing constraints., SyntheticProjectSpec, build_demo_project_data() (+4 more)

### Community 54 - "Candidate Search and Scoring"
Cohesion: 0.20
Nodes (9): CandidateEvaluationCache, CandidateEvaluationOutcome, Scenario-independent result of the expensive evaluation pipeline., Bind a cached evaluation to a materialized scenario identity., In-memory cache keyed by design and complete evaluation context., _outcome(), Tests for deterministic search caching and fingerprinting., test_candidate_evaluation_cache_evicts_oldest_entry() (+1 more)

### Community 55 - "Request and Response Schemas"
Cohesion: 0.25
Nodes (13): post, Execute the complete end-to-end Surge optimisation workflow., run_optimisation(), Explicitly map the API request to Surge domain models., to_workflow_invocation(), OptimiseProjectRequest, generate_corpus(), Path (+5 more)

### Community 56 - "Geospatial Data Processing"
Cohesion: 0.31
Nodes (9): parse_geojson(), Any, BaseGeometry, Serialize a Shapely geometry back into a GeoJSON geometry dictionary., Parse a GeoJSON dictionary (Feature or Geometry) into a Shapely geometry. If…, serialize_geometry(), test_parse_geojson_feature(), test_parse_geojson_geometry_only() (+1 more)

### Community 57 - "Regression Test Coverage"
Cohesion: 0.31
Nodes (4): Complete result of one ``generate_pnc_scenarios`` call. Attributes ----------…, ScenarioGenerationResult, Every candidate satisfies PY-014 network integrity requirements., TestStructuralIntegrity

### Community 58 - "Request and Response Schemas"
Cohesion: 0.33
Nodes (3): EngineeringScoringWeightsRequest, model_validator, Self

### Community 59 - "Geospatial Data Processing"
Cohesion: 0.28
Nodes (7): _extract_features(), Any, Point, Picks the substation feeders should connect to when more than one is supplied.…, _select_primary_substation(), _validate_capacity(), _validate_point_coords()

### Community 60 - "Regression Test Coverage"
Cohesion: 0.28
Nodes (6): _apply_long_edge_penalty(), Graph, Return a copy of *graph* with non-uniform edge weights. Transformation: ``w' =…, Verify _apply_long_edge_penalty applies non-uniform transformation., If all weights were multiplied by the same factor, MST would be unchanged.…, TestLongEdgePenaltyIsNonUniform

### Community 61 - "ADR-003 ML Ranking"
Cohesion: 0.25
Nodes (8): Deterministic engineering safety boundary, ADR-003 ML Ranking document, Future ML candidate pre-ranking (deferred plan), Verified training-data prerequisite for ML, Journal 2026-08-04, PostGIS and GIS next steps (historical plan), Repository genesis (historical journal log), Obsidian vault setup (historical journal log)

### Community 62 - "Electrical Network Validation"
Cohesion: 0.38
Nodes (4): CandidateElectricalEvaluationError, Exception, Execution error evaluating an individual candidate network. This indicates a…, Electrical feasibility screening and validation.

### Community 63 - "Geospatial Data Processing"
Cohesion: 0.43
Nodes (5): BaseGeometry, Validates a shapely geometry. If it's invalid (e.g., self-intersecting…, validate_geometry(), test_validate_invalid_geometry(), test_validate_valid_geometry()

### Community 64 - "Regression Test Coverage"
Cohesion: 0.29
Nodes (3): Two runs with identical inputs produce identical structural results., Shuffling turbine input order must not affect the output., TestDeterminism

### Community 65 - "Regression Test Coverage"
Cohesion: 0.33
Nodes (6): Deterministic Synthetic Corpus Layouts, Electrical Evaluation Variation, Non-Round-Trip Provenance Limit, Provenance Classification Vocabulary, Python Contract Fixture, Spatial Constraint Processing Behavior

### Community 67 - "2026-08-16-ark"
Cohesion: 0.50
Nodes (4): Candidate search reliability work (historical journal log), Journal 2026-08-16 ARK, Land context integration (historical journal log), Pole micro-siting work (historical journal log)

### Community 68 - "Python Libraries and Utilities"
Cohesion: 0.67
Nodes (3): Current MVP Routed Network Baseline, Implemented PNC and Validation Modules, Planned Post-MVP ML Ranking and GIS Rasterization

## Knowledge Gaps
- **153 isolated node(s):** `SyntheticProjectSpec`, `Electrical Evaluation Variation`, `Spatial Constraint Processing Behavior`, `Implemented PNC and Validation Modules`, `Planned Post-MVP ML Ranking and GIS Rasterization` (+148 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 704 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ProjectSpatialData` connect `Regression Test Coverage` to `Routing and Graph Algorithms`, `Electrical Network Validation`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Historical Engineering Journal`, `Network Optimisation Design`, `PNC Network Assembly`, `Regression Test Coverage`, `Python Engine Engineering`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Geospatial Data Processing`, `Regression Test Coverage`, `Regression Test Coverage`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `CostSurface` connect `Routing and Graph Algorithms` to `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Network Optimisation Design`, `PNC Network Assembly`, `Regression Test Coverage`, `Python Engine Engineering`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Geospatial Data Processing`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Geospatial Data Processing`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `ProjectPNCNetwork` connect `PNC Network Assembly` to `System Architecture`, `Candidate Search and Scoring`, `Lifecycle Cost Evaluation`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Regression Test Coverage`, `Electrical Network Validation`, `Network Optimisation Design`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Python Libraries and Utilities`, `Python Engine Engineering`, `Regression Test Coverage`, `Candidate Search and Scoring`, `Regression Test Coverage`, `Routing and Graph Algorithms`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Regression Test Coverage`, `Geospatial Data Processing`, `Regression Test Coverage`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 64 inferred relationships involving `ProjectSpatialData` (e.g. with `build_project_graph()` and `group_wtgs()`) actually correct?**
  _`ProjectSpatialData` has 64 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `CostSurface` (e.g. with `a_star()` and `route_collector_topology()`) actually correct?**
  _`CostSurface` has 87 INFERRED edges - model-reasoned connections that need verification._
- **Are the 56 inferred relationships involving `LoadFlowConfig` (e.g. with `evaluate_candidate_cost()` and `run_load_flow()`) actually correct?**
  _`LoadFlowConfig` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `ProjectPNCNetwork` (e.g. with `TestDefaultCandidateGeneration` and `_generate_candidate()`) actually correct?**
  _`ProjectPNCNetwork` has 32 INFERRED edges - model-reasoned connections that need verification._

## Extraction audit

Code was extracted locally through AST parsing. Documents were extracted by session subagents, without a paid API call. Actual semantic input/output token counts are unavailable; numeric zero fields are schema placeholders, not measured usage. Documentation requirements, plans, and dated journal entries are source claims, not proof of implemented behavior.

Graph integrity diagnostics: see GRAPH_HEALTH.md. Graphify uses a simple undirected graph, so parallel relationship types can collapse into one edge. Raw extraction is retained in extraction.json, including unresolved endpoints.

Cross-corpus links: 167 inferred references from exact unique symbol mentions, confidence 0.85; see cross-corpus-links.json for line evidence.

Source extraction warning: the Python graph drops 481 unresolved-endpoint edges and collapses 1,724 same-endpoint relationships in the simple graph view. The complete raw source fragments are retained in ../../optimisation-python/graphify-out/extraction.json and ../../obsidian-vault/graphify-out/extraction.json; source diagnostics are retained alongside them. pyproject.toml produced no AST nodes.

The Obsidian graph additionally collapses 99 reciprocal document-link pairs in its undirected view; the raw vault extraction retains both directions.
