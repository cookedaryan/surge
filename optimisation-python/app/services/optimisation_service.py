from app.schemas.optimise import (
    OptimisationMetrics,
    OptimisationRequest,
    OptimisationResponse,
)
from app.gis.preprocessing import process_project_data

class OptimisationService:
    def optimise(
        self,
        payload: OptimisationRequest,
    ) -> OptimisationResponse:
        """Day-1 optimisation pipeline stub."""

        # Parse and project GIS models
        spatial_data = process_project_data(
            wtg_geojson=payload.wtg_geojson,
            substation_geojson=payload.substation_geojson
        )

        return OptimisationResponse(
            request_id=payload.request_id,
            status="success",
            scenario=payload.scenario,
            feeder_routes_geojson={
                "type": "FeatureCollection",
                "features": [],
            },
            metrics=OptimisationMetrics(
                feeder_count=len(spatial_data.turbines),
                total_length_m=0.0,
                estimated_cost=None,
                message=f"Pipeline initialized. Projected into {spatial_data.projected_crs.name}",
            ),
        )
