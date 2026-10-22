"""Server-controlled search activation. Owned by L2 (WP4-1).

Stage 0 stub: search stays disabled regardless of flags or request content.
"""

from app.contracts.resolution import SEARCH_DISABLED, SearchActivation
from app.core.config import Settings
from app.schemas.optimise import OptimisationRequest


def resolve_search_activation(
    payload: OptimisationRequest,
    settings: Settings,
) -> SearchActivation:
    return SEARCH_DISABLED
