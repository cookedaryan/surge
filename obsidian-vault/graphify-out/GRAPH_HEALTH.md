[graphify] MultiDiGraph edge-collapse diagnostic
input: <in-memory>
input_stage: provided JSON (normal graph.json is post-build)
effective_directed: <direct-call>
nodes: 254
unverified_code_nodes: 0
raw_edges: 653
valid_candidate_edges: 653
missing_endpoint_edges: 0
dangling_endpoint_edges: 0
self_loop_edges: 0
exact_duplicate_edges: 0
directed_unique_endpoint_pairs: 653
directed_same_endpoint_collapsed_edges: 0
undirected_unique_endpoint_pairs: 554
undirected_same_endpoint_collapsed_edges: 99
same_endpoint_group_count: 0
relation_variant_groups: 0
source_file_variant_groups: 0
source_location_variant_groups: 0
context_variant_groups: 0
post_build_graph_type: Graph
post_build_edges: 554
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
note: normal graph.json is post-build; raw producer loss must be measured earlier.