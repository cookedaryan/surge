from fastapi import APIRouter, HTTPException

from app.optimisation.orchestrator import optimise_project
from app.optimisation.workflow_models import (
    OptimisationInputError,
    WorkflowFailureCode,
)
from app.schemas.legacy_mapping import (
    legacy_to_workflow_invocation,
    to_legacy_api_response,
)
from app.schemas.optimise import (
    OptimisationRequest,
    OptimisationResponse,
)

router = APIRouter()


@router.post(
    "/optimise",
    response_model=OptimisationResponse,
    response_model_exclude_none=True,
)
def run_optimisation(
    payload: OptimisationRequest,
) -> OptimisationResponse:
    try:
        invocation = legacy_to_workflow_invocation(payload)
        result = optimise_project(invocation.project_input, invocation.config)
    except (OptimisationInputError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    generation_failure = next(
        (
            failure
            for failure in result.failures
            if failure.code == WorkflowFailureCode.GENERATION_FAILED
        ),
        None,
    )
    if generation_failure is not None:
        raise HTTPException(status_code=422, detail=generation_failure.message)

    return to_legacy_api_response(result, payload)
