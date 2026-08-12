from app.algorithms.physical_routing import route_collector_topology
from app.algorithms.route_graph import build_project_graph
from app.algorithms.route_refinement import refine_routing_result
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
        """Runs the complete optimisation pipeline."""

        # Phase 1: Spatial Data Preprocessing
        spatial_data = process_project_data(
            wtg_geojson=payload.wtg_geojson,
            substation_geojson=payload.substation_geojson,
        )

        # Phase 2: Topology Graph Generation
        topology_graph = build_project_graph(spatial_data)

        # Phase 3: Capacity-Constrained WTG Grouping
        grouping_result = group_wtgs(
            spatial_data, payload.electrical_params.feeder_capacity_mw
        )

        # SURGE-PY-006: MST network generation
        topology_result = build_feeder_mst(topology_graph, grouping_result)

        # SURGE-PY-007 to 009: Physical Routing and Geometry Refinement
        cost_surface = build_project_cost_surface(spatial_data)
        physical_routes = route_collector_topology(
            topology_result, topology_graph, cost_surface
        )
        refined_routes = refine_routing_result(physical_routes, cost_surface)
        total_length_m = refined_routes.total_refined_length_m

        transformer = get_transformer(spatial_data.projected_crs, WGS84_CRS)
        feeder_features = []
        for route in refined_routes.routes:
            coords = []
            for x, y in route.geometry.coords:
                lon, lat = transformer.transform(x, y)
                coords.append([lon, lat])

            feeder_features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "feederName": route.feeder_id,
                        "edge": f"{route.start_node_id}-{route.end_node_id}",
                        "length_m": route.refined_length_m,
                        "traversal_cost": route.refined_traversal_cost,
                        "original_length_m": route.original_length_m,
                        "refined_length_m": route.refined_length_m,
                        "original_traversal_cost": route.original_traversal_cost,
                        "refined_traversal_cost": route.refined_traversal_cost,
                    },
                    "geometry": {"type": "LineString", "coordinates": coords},
                }
            )

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
                    "Pipeline completed. Refined routes over the uniform "
                    "cost surface. "
                    f"Projected into {spatial_data.projected_crs.name}"
                ),
            ),
        )
