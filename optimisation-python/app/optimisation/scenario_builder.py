from __future__ import annotations

import networkx as nx

from app.algorithms.physical_routing import RouteNotFoundError, route_collector_topology
from app.algorithms.route_refinement import refine_routing_result
from app.algorithms.topology import CollectorTopologyResult
from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData
from app.optimisation.scenario_models import (
    AttemptOutcome,
    PNCScenario,
    ScenarioParameters,
)
from app.pnc.assembly import assemble_pnc_network
from app.pnc.errors import PNCAssemblyError


def materialize_candidate_design(
    topology: CollectorTopologyResult,
    working_graph: nx.Graph,
    cost_surface: CostSurface,
    project: ProjectSpatialData,
    project_id: str,
    scenario_id: str,
    strategy: str,
    parameters: ScenarioParameters,
    comparison_group_id: str,
    topology_fingerprint: str,
) -> tuple[PNCScenario | None, AttemptOutcome, str]:
    """Materialize a logical topology into a fully routed PNCScenario."""
    # Physical routing (A*)
    try:
        physical_routes = route_collector_topology(
            topology, working_graph, cost_surface
        )
        refined_routes = refine_routing_result(physical_routes, cost_surface)
    except RouteNotFoundError as exc:
        return None, AttemptOutcome.ROUTING_FAILED, str(exc)

    # PNC assembly
    try:
        network = assemble_pnc_network(
            project_id=project_id,
            project=project,
            topology=topology,
            refined_routes=refined_routes,
        )
    except (PNCAssemblyError, ValueError) as exc:
        return None, AttemptOutcome.ASSEMBLY_FAILED, str(exc)

    scenario = PNCScenario(
        scenario_id=scenario_id,
        strategy=strategy,
        parameters=parameters,
        network=network,
        topology_fingerprint=topology_fingerprint,
        comparison_group_id=comparison_group_id,
        feeder_count=network.feeder_count,
        wtg_count=network.wtg_count,
        segment_count=network.segment_count,
        total_route_length_m=network.total_route_length_m,
        route_length_by_feeder=network.route_length_by_feeder,
        wtg_count_by_feeder=network.wtg_count_by_feeder,
    )
    return scenario, AttemptOutcome.ACCEPTED, ""
