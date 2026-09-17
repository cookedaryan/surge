"""Run cancellation endpoint (C7). Owned by L3 (WP4-9a).

Stage 0 stub: the route exists so Java can target a fixed path, but it answers
501 ``NOT_IMPLEMENTED`` until cancellation is implemented.
"""

from fastapi import APIRouter, HTTPException

from app.contracts.codes import ContractErrorCode

router = APIRouter()


@router.post("/runs/{run_id}/cancel", status_code=202)
def cancel_run(run_id: str) -> dict[str, str]:
    raise HTTPException(
        status_code=501,
        detail={
            "code": ContractErrorCode.NOT_IMPLEMENTED.value,
            "message": "Run cancellation is not available on this deployment.",
        },
    )
