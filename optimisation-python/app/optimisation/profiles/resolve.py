"""Profile resolution for V1 requests. Owned by L3 (WP3-1, WP3-4).

Stage 0 stub: an absent profile resolves to V0; any explicit profile is refused
with ``PROFILE_NOT_SUPPORTED`` rather than being silently ignored.
"""

from app.contracts.codes import ContractErrorCode
from app.contracts.errors import ContractError
from app.contracts.resolution import V0_PROFILE_RESOLUTION, ProfileResolution
from app.core.config import Settings
from app.schemas.optimise import OptimisationRequest


def resolve_profile(
    payload: OptimisationRequest,
    settings: Settings,
) -> ProfileResolution:
    if payload.profile is None:
        return V0_PROFILE_RESOLUTION
    raise ContractError(
        ContractErrorCode.PROFILE_NOT_SUPPORTED,
        "Versioned profiles are not available on this deployment.",
    )
