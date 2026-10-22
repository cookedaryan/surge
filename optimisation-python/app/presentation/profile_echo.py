"""Effective profile, hashes and flag echo for the V1 response. Owned by L3 (WP3-7a).

Answers "what actually produced this response": which profile ranked it, which
policy values that profile carried, which metric registry the numbers came from,
and which deployment flags were on. The G0 claim is that every recommendation can
be reproduced from the recorded evidence, and a recommendation cannot be reproduced
without knowing the policy that made it.

Three hashes, three different questions:

- ``policy_hash`` identifies **this profile's own definition** - its terms, weights,
  reference ranges and tie-breaks. Two runs with the same policy hash ranked under
  the same policy, whatever else changed around them.
- ``definition_hash`` identifies **the whole registry**, and is the value Java
  compares at startup (WP3-6b). It changes when any profile changes, which is what
  makes it a handshake.
- ``generation_settings_hash`` identifies the profile's generation settings, which
  are routing inputs rather than ranking policy and are shown apart from it.

The block is absent when both C5 flags are off, which is V0. With either flag on it
is published even if no profile resolved, because the flag state is itself part of
what produced the response; the profile fields are then null rather than invented.
"""

from app.contracts.canonical_json import canonical_sha256
from app.contracts.metric_registry_version import METRIC_REGISTRY_VERSION
from app.contracts.profiles import ProfileDefinition
from app.contracts.resolution import ResponseContext
from app.contracts.response import EffectiveProfile
from app.optimisation.profiles import registry
from app.optimisation.workflow_models import OptimisationWorkflowResult


def build_effective_profile(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> EffectiveProfile | None:
    if not context.profiles_enabled and not context.search_enabled:
        return None

    definition = _resolved_definition(context)
    return EffectiveProfile(
        profile_id=context.profile.profile_id,
        profile_version=context.profile.profile_version,
        policy_hash=policy_hash(definition) if definition is not None else None,
        definition_hash=registry.registry_hash(),
        metric_registry_version=METRIC_REGISTRY_VERSION,
        generation_settings_hash=(
            generation_settings_hash(definition) if definition is not None else None
        ),
        profiles_enabled=context.profiles_enabled,
        search_enabled=context.search_enabled,
    )


def policy_hash(definition: ProfileDefinition) -> str:
    """Hash of one profile definition: the policy that ranked this run."""
    return canonical_sha256(definition.model_dump(mode="json"))


def generation_settings_hash(definition: ProfileDefinition) -> str:
    """Hash of the profile's generation settings, separate from its ranking policy."""
    return canonical_sha256(definition.generation_settings)


def _resolved_definition(context: ResponseContext) -> ProfileDefinition | None:
    profile_id = context.profile.profile_id
    version = context.profile.profile_version
    if profile_id is None or version is None:
        return None
    return registry.definition_for(profile_id, version)
