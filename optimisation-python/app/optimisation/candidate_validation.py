"""Safe structural validation of candidate topologies."""

import math

import networkx as nx

from app.algorithms.route_graph import turbine_node_id
from app.algorithms.topology import CollectorTopologyResult
from app.algorithms.wtg_grouping import FeederGroupingResult
from app.optimisation.workflow_models import ProjectInput


def validate_candidate_structure(
    grouping: FeederGroupingResult,
    topology: CollectorTopologyResult,
    project_input: ProjectInput,
    substation_node_id: str,
) -> bool:
    """
    Strictly validates hard structural invariants for a candidate.
    Returns True if valid, False if it provably violates an invariant.
    Does not use heuristics.
    """
    turbines_by_id = {
        turbine.turbine_id: turbine for turbine in project_input.project_data.turbines
    }
    all_turbines = set(turbines_by_id)
    assignments_by_id = {
        assignment.feeder_id: assignment for assignment in grouping.assignments
    }
    feeders_by_id = {feeder.feeder_id: feeder for feeder in topology.feeders}

    if (
        len(assignments_by_id) != len(grouping.assignments)
        or len(feeders_by_id) != len(topology.feeders)
        or grouping.feeder_count != len(grouping.assignments)
        or set(assignments_by_id) != set(feeders_by_id)
    ):
        return False

    # Check 1: Exactly one assignment per WTG
    assigned_wtgs = set()
    for assignment in grouping.assignments:
        for t_id in assignment.turbine_ids:
            if t_id in assigned_wtgs:
                return False  # WTG assigned twice
            assigned_wtgs.add(t_id)

    if assigned_wtgs != all_turbines:
        return False  # Missing or invalid WTG

    # Check 2: Feeder capacity hard limit and aggregate consistency
    for assignment in grouping.assignments:
        calculated_capacity = math.fsum(
            turbines_by_id[turbine_id].capacity_mw or 0.0
            for turbine_id in assignment.turbine_ids
        )
        if (
            not math.isfinite(assignment.total_capacity_mw)
            or not math.isclose(
                assignment.total_capacity_mw,
                calculated_capacity,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
            or calculated_capacity > project_input.feeder_capacity_mw + 1e-9
        ):
            return False

    for feeder in topology.feeders:
        mst = feeder.mst_graph
        assignment = assignments_by_id[feeder.feeder_id]
        expected_nodes = {substation_node_id} | {
            turbine_node_id(turbine_id) for turbine_id in assignment.turbine_ids
        }
        if set(mst) != expected_nodes or not nx.is_tree(mst):
            return False

    return True
