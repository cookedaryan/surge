from fastapi import APIRouter, HTTPException

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
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
