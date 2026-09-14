[graphify] MultiDiGraph edge-collapse diagnostic
input: <in-memory>
input_stage: provided JSON (normal graph.json is post-build)
effective_directed: <direct-call>
nodes: 2061
unverified_code_nodes: 0
raw_edges: 9594
valid_candidate_edges: 9113
missing_endpoint_edges: 0
dangling_endpoint_edges: 481
self_loop_edges: 0
exact_duplicate_edges: 214
directed_unique_endpoint_pairs: 7389
directed_same_endpoint_collapsed_edges: 1724
undirected_unique_endpoint_pairs: 7389
undirected_same_endpoint_collapsed_edges: 1724
same_endpoint_group_count: 1343
relation_variant_groups: 1322
source_file_variant_groups: 0
source_location_variant_groups: 9
context_variant_groups: 26
post_build_graph_type: Graph
post_build_edges: 7389
producer_suppression_sites: 12
producer_suppression_examples:
  - L1206 seen_ids arity=unknown
  - L1739 seen_ids arity=unknown
  - L1741 seen_doc_refs arity=unknown
  - L2111 seen_ids arity=unknown
  - L2258 seen_ids arity=unknown
  - L2896 seen_keys arity=unknown
  - L3065 seen_keys arity=unknown
  - L4757 seen_ids arity=unknown
examples:
  - app_algorithms_pole_micro_siting_optimize_poles -> app_algorithms_pole_placement_collectorpoleresult edges=5 relations=['calls', 'references', 'uses'] locations=['L283', 'L284', 'L420'] contexts=['', 'call', 'generic_arg', 'parameter_type']
  - app_gis_constraints_apply_constraint_layers -> app_gis_cost_surface_costsurface edges=5 relations=['calls', 'references', 'uses'] locations=['L185', 'L186', 'L219'] contexts=['', 'call', 'parameter_type', 'return_type']
  - app_optimisation_candidate_search_apply_grouping_mutation -> app_algorithms_wtg_grouping_feedergroupingresult edges=5 relations=['calls', 'references', 'uses'] locations=['L240', 'L241', 'L265'] contexts=['', 'call', 'parameter_type', 'return_type']
  - app_optimisation_candidate_search_apply_topology_mutation -> app_algorithms_topology_collectortopologyresult edges=5 relations=['calls', 'references', 'uses'] locations=['L268', 'L269', 'L304'] contexts=['', 'call', 'parameter_type', 'return_type']
  - app_costing_lifecycle_add_fallback_land_costs -> app_costing_models_costlineitem edges=4 relations=['calls', 'references', 'uses'] locations=['L39', 'L43', 'L64'] contexts=['', 'call', 'generic_arg']
note: normal graph.json is post-build; raw producer loss must be measured earlier.