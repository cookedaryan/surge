"""Profile resolution for V1 requests. Owned by L3 (WP3-1, WP3-4).

Every request is validated first (WP3-1): a bad value is refused with a stable C3
code before anything is parsed or optimised. Then:

- **No profile** resolves to V0. WP5-2 applies the C5/C12 generation-schedule gate
  here: the V1 schedule runs only when the profiles or search flag is on, so with
  both flags off the resolution is exactly ``V0_PROFILE_RESOLUTION``.
- **An explicit profile** is checked precisely, in order - unknown ID, unknown
  version, scenario label that does not match the profile, then a definition naming
  an unknown metric - so a client learns exactly what is wrong. Nothing ever
  substitutes Balanced for a profile it does not know.
- **A valid profile resolves** when the C5 profiles flag is on, attaching its
  definition to the scoring config so the recommendation comes from profile
  selection (WP3-3) and the explanation (WP2-7) describes that same ranking. With
  the flag off it is still refused with ``PROFILE_NOT_SUPPORTED``, so V0 deployments
  are unchanged.
"""

from collections.abc import Callable
from dataclasses import replace

from app.contracts.codes import ContractErrorCode
from app.contracts.errors import ContractError
from app.contracts.profiles import (
    ALLOWED_PROFILE_VERSIONS,
    PROFILE_SCENARIO_LABELS,
    ProfileDefinition,
    ProfileId,
)
from app.contracts.request import ProfileSelection
from app.contracts.resolution import V0_PROFILE_RESOLUTION, ProfileResolution
from app.core.config import Settings
from app.optimisation.profiles import registry
from app.optimisation.profiles.metrics import KNOWN_METRICS
from app.optimisation.profiles.validation import validate_request
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
    validate_request(payload)

    if payload.profile is None:
        if settings.new_generation_schedule_enabled:
            return V0_PROFILE_WITH_V1_SCHEDULE
        return V0_PROFILE_RESOLUTION

    definition = definition_for_request(payload.profile, payload.scenario)
    if not settings.surge_profiles_enabled:
        raise ContractError(
            ContractErrorCode.PROFILE_NOT_SUPPORTED,
            "Versioned profiles are not enabled on this deployment.",
        )
    return ProfileResolution(
        profile_id=definition.profile_id.value,
        profile_version=definition.version,
        configure=_apply_profile(definition),
    )


def _apply_profile(
    definition: ProfileDefinition,
) -> Callable[[OptimisationConfig], OptimisationConfig]:
    """Attach the profile to the scoring config, and change nothing else.

    The profile has to reach the recommendation, and the only route that stays
    inside L3's paths is the scoring config: ``OptimisationConfig`` is frozen and
    the orchestrator belongs to L2. ``evaluate_cohort`` reads it and orders the
    cohort by profile selection instead of the V0 weights.
    """

    def configure(config: OptimisationConfig) -> OptimisationConfig:
        return replace(
            config,
            scenario=replace(
                config.scenario, generation_schedule=GenerationSchedule.V1
            ),
            scoring=replace(config.scoring, profile=definition),
        )

    return configure


def definition_for_request(
    selection: ProfileSelection, scenario: str
) -> ProfileDefinition:
    """The registry definition an explicit profile names, or a stable error.

    Checked in a fixed order so a request with several defects always reports the
    same one. Never returns a substitute: an unknown profile is an error.
    """
    try:
        profile_id = ProfileId(selection.id)
    except ValueError:
        raise ContractError(
            ContractErrorCode.UNKNOWN_PROFILE,
            f"Unknown profile {selection.id!r}. Allowed: "
            + ", ".join(sorted(item.value for item in ProfileId))
            + ".",
        ) from None

    allowed_versions = ALLOWED_PROFILE_VERSIONS[profile_id]
    if selection.version not in allowed_versions:
        raise ContractError(
            ContractErrorCode.UNKNOWN_PROFILE_VERSION,
            f"Unknown version {selection.version!r} for profile {profile_id.value}. "
            f"Allowed: {', '.join(allowed_versions)}.",
        )

    expected_label = PROFILE_SCENARIO_LABELS[profile_id]
    if scenario != expected_label:
        raise ContractError(
            ContractErrorCode.PROFILE_SCENARIO_MISMATCH,
            f"Profile {profile_id.value} must be sent with scenario "
            f"{expected_label!r}, not {scenario!r}.",
        )

    definition = registry.definition_for(profile_id.value, selection.version)
    if definition is None:
        # The registry checks itself against the allow-list at import, so this is a
        # deployment defect; it is still an error, never a fallback.
        raise ContractError(
            ContractErrorCode.UNKNOWN_PROFILE_VERSION,
            f"No definition is registered for {profile_id.value} "
            f"version {selection.version}.",
        )

    # No request field names a metric; profile terms do. So an unknown metric can
    # only come from a definition, which the registry also checks at import. This
    # is the request-time guard for a definition loaded some other way.
    for term in definition.terms:
        if term.metric not in KNOWN_METRICS:
            raise ContractError(
                ContractErrorCode.UNKNOWN_METRIC,
                f"Profile {profile_id.value} names unknown metric {term.metric!r}.",
            )
    return definition
