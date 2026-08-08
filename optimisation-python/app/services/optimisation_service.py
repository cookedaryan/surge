import networkx as nx

from app.algorithms.route_graph import build_project_graph
from app.algorithms.wtg_grouping import group_wtgs
from app.gis.preprocessing import process_project_data
from app.schemas.optimise import (
    OptimisationMetrics,
    OptimisationRequest,
    OptimisationResponse,
)


class OptimisationService:
    def optimise(
        self,
        payload: OptimisationRequest,
    ) -> OptimisationResponse:
        """Day-1 optimisation pipeline stub."""

        # Phase 1: Spatial Data Preprocessing
        spatial_data = process_project_data(
            wtg_geojson=payload.wtg_geojson,
            substation_geojson=payload.substation_geojson
        )

        # Phase 2: Topology Graph Generation
        topology_graph = build_project_graph(spatial_data)
        
        # Phase 3: Capacity-Constrained WTG Grouping
        grouping_result = group_wtgs(
            spatial_data, 
            payload.electrical_params.feeder_capacity_mw
        )

        # TODO: Implement MST network generation (SURGE-PY-006)
        
        return OptimisationResponse(
            request_id=payload.request_id,
            status="success",
            scenario=payload.scenario,
            feeder_routes_geojson={
                "type": "FeatureCollection",
                "features": [],
            },
            metrics=OptimisationMetrics(
                feeder_count=grouping_result.feeder_count,
                total_length_m=0.0,
                estimated_cost=None,
                message=(
                    f"Pipeline initialized. "
                    f"Projected into {spatial_data.projected_crs.name}"
                ),
            ),
        )
