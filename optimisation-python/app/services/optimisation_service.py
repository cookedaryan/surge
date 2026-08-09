from app.algorithms.route_graph import build_project_graph
from app.algorithms.topology import build_feeder_mst
from app.algorithms.wtg_grouping import group_wtgs
from app.gis.crs import WGS84_CRS, get_transformer
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

        # SURGE-PY-006: MST network generation
        topology_result = build_feeder_mst(topology_graph, grouping_result)
        total_length_m = sum(f.total_length_m for f in topology_result.feeders)
        
        transformer = get_transformer(spatial_data.projected_crs, WGS84_CRS)
        feeder_features = []
        for feeder in topology_result.feeders:
            for u, v in feeder.mst_edges:
                p1 = topology_graph.nodes[u]["geometry"]
                p2 = topology_graph.nodes[v]["geometry"]
                
                lon1, lat1 = transformer.transform(p1.x, p1.y)
                lon2, lat2 = transformer.transform(p2.x, p2.y)
                
                feeder_features.append({
                    "type": "Feature",
                    "properties": {
                        "feeder_id": feeder.feeder_id,
                        "edge": f"{u}-{v}"
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[lon1, lat1], [lon2, lat2]]
                    }
                })
        
        return OptimisationResponse(
            request_id=payload.request_id,
            status="success",
            scenario=payload.scenario,
            feeder_routes_geojson={
                "type": "FeatureCollection",
                "features": feeder_features,
            },
            metrics=OptimisationMetrics(
                feeder_count=grouping_result.feeder_count,
                total_length_m=total_length_m,
                estimated_cost=None,
                message=(
                    f"Pipeline initialized. "
                    f"Projected into {spatial_data.projected_crs.name}"
                ),
            ),
        )
