from fastapi import APIRouter

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
    return optimisation_service.optimise(payload)
