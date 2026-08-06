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
        """Execute the SURGE route optimisation pipeline.

        Day-1 implementation returns an empty GeoJSON result.
        """

        return OptimisationResponse(
            request_id=payload.request_id,
            status="success",
            scenario=payload.scenario,
            feeder_routes_geojson={
                "type": "FeatureCollection",
                "features": [],
            },
            metrics=OptimisationMetrics(
                feeder_count=0,
                total_length_m=0.0,
                message="Optimisation pipeline stub initialized",
            ),
        )
