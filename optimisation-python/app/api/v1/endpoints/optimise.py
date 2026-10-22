from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.contracts.errors import ContractError
from app.contracts.resolution import ResponseContext
from app.core.config import get_settings
from app.optimisation.orchestrator import optimise_project
from app.optimisation.profiles.resolve import resolve_profile
from app.optimisation.run_guard import (
    RunCancelledError,
    RunGuardContext,
    RunGuardStop,
    build_run_guard,
)
from app.optimisation.search_activation import resolve_search_activation
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

# Contract C7: the header Java uses to name a run so it can later cancel it.
RUN_ID_HEADER = "X-Surge-Run-Id"


@router.post(
    "/optimise",
    response_model=OptimisationResponse,
    response_model_exclude_none=True,
)
def run_optimisation(
    payload: OptimisationRequest,
    run_id: Annotated[str | None, Header(alias=RUN_ID_HEADER)] = None,
) -> OptimisationResponse:
    settings = get_settings()
    try:
        profile = resolve_profile(payload, settings)
        search = resolve_search_activation(payload, settings)
    except ContractError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.detail()) from exc

    run_guard = build_run_guard(RunGuardContext(run_id=run_id))
    try:
        invocation = legacy_to_workflow_invocation(payload)
        config = search.configure(profile.configure(invocation.config))
        result = optimise_project(
            invocation.project_input,
            config,
            run_guard=run_guard,
        )
    except (OptimisationInputError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RunCancelledError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.reason.value, "message": str(exc)},
        ) from exc
    except RunGuardStop as exc:
        # A stop the owning search/orchestration code did not handle.
        raise HTTPException(
            status_code=503,
            detail={"code": exc.reason.value, "message": str(exc)},
        ) from exc

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

    context = ResponseContext(
        profile=profile,
        search=search,
        profiles_enabled=settings.surge_profiles_enabled,
        search_enabled=settings.surge_search_enabled,
        run_id=run_id,
    )
    return to_legacy_api_response(result, payload, context)
