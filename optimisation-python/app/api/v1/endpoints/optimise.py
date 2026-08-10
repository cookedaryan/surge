from fastapi import APIRouter, HTTPException

from app.algorithms.physical_routing import RouteNotFoundError
from app.schemas.optimise import (
    OptimisationRequest,
    OptimisationResponse,
)
from app.services.optimisation_service import OptimisationService

router = APIRouter()

optimisation_service = OptimisationService()


@router.post(
    "/optimise",
    response_model=OptimisationResponse,
)
def run_optimisation(
    payload: OptimisationRequest,
) -> OptimisationResponse:
    try:
        return optimisation_service.optimise(payload)
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
