import math

import networkx as nx

from app.models.spatial import ProjectSpatialData


def turbine_node_id(turbine_id: str) -> str:
    """Helper to ensure globally unique string IDs for WTGs."""
    return f"wtg:{turbine_id}"


def substation_node_id(substation_id: str) -> str:
    """Helper to ensure globally unique string IDs for Substations."""
    return f"substation:{substation_id}"


def build_project_graph(project: ProjectSpatialData) -> nx.Graph:
    """
    Constructs an undirected complete topology graph from project spatial data.
    Every node represents a WTG or Substation, and every edge is a candidate
    connection between them.
    
    Nodes store metric coordinates (x, y), type, capacity, and geometry.
    Edges store the straight-line Euclidean distance (distance_m) and weight.
    """
    graph = nx.Graph()
    
    # Store global project metadata on the graph
    graph.graph["crs"] = project.projected_crs
    graph.graph["graph_type"] = "collector_candidate"
    
    # Collect all nodes for later complete graph iteration
    all_nodes = []
    
    # 1. Add Substation Node
    sub_id = substation_node_id(project.substation.substation_id)
    graph.add_node(
        sub_id,
        type="substation",
        x=project.substation.location.x,
        y=project.substation.location.y,
        capacity_mw=project.substation.capacity_mw,
        geometry=project.substation.location,
    )
    all_nodes.append((sub_id, project.substation.location))
    
    # 2. Add WTG Nodes
    # Using a set to enforce uniqueness (already handled in preprocessing)
    seen_ids = set()
    seen_ids.add(sub_id)
    
    for turbine in project.turbines:
        wtg_id = turbine_node_id(turbine.turbine_id)
        if wtg_id in seen_ids:
            raise ValueError(f"Duplicate node ID encountered: {wtg_id}")
        seen_ids.add(wtg_id)
        
        graph.add_node(
            wtg_id,
            type="wtg",
            x=turbine.location.x,
            y=turbine.location.y,
            capacity_mw=turbine.capacity_mw,
            geometry=turbine.location,
        )
        all_nodes.append((wtg_id, turbine.location))
        
    # 3. Create Complete Graph (Connect every node to every other node)
    # E = N(N-1)/2 edges
    num_nodes = len(all_nodes)
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            id_a, geom_a = all_nodes[i]
            id_b, geom_b = all_nodes[j]
            
            # Straight-line Euclidean distance (metric)
            distance = math.sqrt((geom_a.x - geom_b.x)**2 + (geom_a.y - geom_b.y)**2)
            
            graph.add_edge(
                id_a,
                id_b,
                distance_m=distance,
                weight=distance,  # Baseline Euclidean weighting for now
            )
            
    return graph
