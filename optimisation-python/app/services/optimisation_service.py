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
                estimated_cost=None,
                message="Optimisation pipeline stub initialized",
            ),
        )
