from app.algorithms.physical_routing import route_collector_topology
from app.algorithms.route_graph import build_project_graph
from app.algorithms.topology import build_feeder_mst
from app.algorithms.wtg_grouping import group_wtgs
from app.gis.cost_surface import build_project_cost_surface
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
        
        # SURGE-PY-007 & 008: Physical Routing
        cost_surface = build_project_cost_surface(spatial_data)
        physical_routes = route_collector_topology(topology_result, topology_graph, cost_surface)
        total_length_m = physical_routes.total_length_m
        
        transformer = get_transformer(spatial_data.projected_crs, WGS84_CRS)
        feeder_features = []
        for route in physical_routes.routes:
            coords = []
            for x, y in route.geometry.coords:
                lon, lat = transformer.transform(x, y)
                coords.append([lon, lat])
                
            feeder_features.append({
                "type": "Feature",
                "properties": {
                    "feeder_id": route.feeder_id,
                    "edge": f"{route.start_node_id}-{route.end_node_id}",
                    "length_m": route.length_m,
                    "traversal_cost": route.traversal_cost
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
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
