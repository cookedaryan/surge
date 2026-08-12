import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.optimisation.orchestrator import optimise_project
from app.optimisation.workflow_models import OptimisationInputError
from app.schemas.v2.domain_mapping import to_api_response, to_workflow_invocation
from app.schemas.v2.optimise import OptimiseProjectRequest, OptimiseProjectResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/optimise",
    response_model=OptimiseProjectResponse,
    response_model_exclude_none=True,
)
def run_optimisation(
    payload: OptimiseProjectRequest,
) -> OptimiseProjectResponse:
    """
    Execute the complete end-to-end Surge optimisation workflow.
    """
    # 1. Map API Request to Domain Input
    try:
        invocation = to_workflow_invocation(payload)
    except (OptimisationInputError, ValidationError) as exc:
        logger.warning(
            "Invalid project input for request %s: %s", payload.request_id, str(exc)
        )
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_INPUT",
                "message": str(exc),
                "request_id": payload.request_id,
            },
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected mapping failure for request %s", payload.request_id
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "MAPPING_INTERNAL_ERROR",
                "message": "The optimisation input mapping could not be completed.",
                "request_id": payload.request_id,
            },
        ) from exc

    # 2. Run Domain Orchestrator (Synchronously)
    try:
        result = optimise_project(
            project_input=invocation.project_input,
            config=invocation.config,
        )
    except Exception as exc:
        logger.exception(
            "Unexpected workflow failure for request %s", payload.request_id
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "OPTIMISATION_INTERNAL_ERROR",
                "message": "The optimisation workflow could not be completed.",
                "request_id": payload.request_id,
            },
        ) from exc

    # 3. Map Domain Result to API Response
    try:
        return to_api_response(
            workflow_result=result,
            request_id=payload.request_id,
            project_id=payload.project_id,
        )
    except Exception as exc:
        logger.exception(
            "Unexpected response mapping failure for request %s", payload.request_id
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RESPONSE_MAPPING_INTERNAL_ERROR",
                "message": "The optimisation output mapping could not be completed.",
                "request_id": payload.request_id,
            },
        ) from exc
