"""Profile definition-hash handshake endpoint (C7). Owned by L3 (WP3-6a).

Stage 0 stub: answers 501 ``NOT_IMPLEMENTED`` until the registry exists. Once
implemented it returns ``definition_hash``, ``metric_registry_version`` and
``contract_pack_version``.
"""

from fastapi import APIRouter, HTTPException

from app.contracts.codes import ContractErrorCode

router = APIRouter()


@router.get("/profiles/definition-hash")
def get_definition_hash() -> dict[str, str]:
    raise HTTPException(
        status_code=501,
        detail={
            "code": ContractErrorCode.NOT_IMPLEMENTED.value,
            "message": "Versioned profiles are not available on this deployment.",
        },
    )
