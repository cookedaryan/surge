"""Profile resolution for V1 requests. Owned by L3 (WP3-1, WP3-4).

Stage 0 stub: an absent profile resolves to V0; any explicit profile is refused
with ``PROFILE_NOT_SUPPORTED`` rather than being silently ignored.

WP5-2 applies the C5/C12 generation-schedule gate here, because the endpoint
resolves the profile on every request: the V1 schedule runs only when the
profiles or search flag is on. With both flags off the resolution is exactly
``V0_PROFILE_RESOLUTION``, so V0 output is unchanged.
"""

from dataclasses import replace

from app.contracts.codes import ContractErrorCode
from app.contracts.errors import ContractError
from app.contracts.resolution import V0_PROFILE_RESOLUTION, ProfileResolution
from app.core.config import Settings
from app.optimisation.scenario_models import GenerationSchedule
from app.optimisation.workflow_models import OptimisationConfig
from app.schemas.optimise import OptimisationRequest


def use_v1_generation_schedule(config: OptimisationConfig) -> OptimisationConfig:
    """Select the V1 generation schedule and change nothing else."""
    return replace(
        config,
        scenario=replace(config.scenario, generation_schedule=GenerationSchedule.V1),
    )


V0_PROFILE_WITH_V1_SCHEDULE = ProfileResolution(
    profile_id=None,
    profile_version=None,
    configure=use_v1_generation_schedule,
)


def resolve_profile(
    payload: OptimisationRequest,
    settings: Settings,
) -> ProfileResolution:
    if payload.profile is None:
        if settings.new_generation_schedule_enabled:
            return V0_PROFILE_WITH_V1_SCHEDULE
        return V0_PROFILE_RESOLUTION
    raise ContractError(
        ContractErrorCode.PROFILE_NOT_SUPPORTED,
        "Versioned profiles are not available on this deployment.",
    )
