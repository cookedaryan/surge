"""Shapes exchanged between the frozen V1 endpoint and level-owned resolvers (S2).

The endpoint resolves the profile (L3) and search activation (L2) before the
run, applies both to the workflow config, and hands both to the response hooks
(S3). A resolver changes behaviour only through ``configure``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.optimisation.workflow_models import OptimisationConfig


def unchanged_config(config: OptimisationConfig) -> OptimisationConfig:
    return config


@dataclass(frozen=True)
class ProfileResolution:
    profile_id: str | None
    profile_version: str | None
    configure: Callable[[OptimisationConfig], OptimisationConfig] = unchanged_config


@dataclass(frozen=True)
class SearchActivation:
    enabled: bool
    configure: Callable[[OptimisationConfig], OptimisationConfig] = unchanged_config


V0_PROFILE_RESOLUTION = ProfileResolution(profile_id=None, profile_version=None)
SEARCH_DISABLED = SearchActivation(enabled=False)


@dataclass(frozen=True)
class ResponseContext:
    """Everything the additive response hooks may read besides the workflow result."""

    profile: ProfileResolution
    search: SearchActivation
    profiles_enabled: bool
    search_enabled: bool
    run_id: str | None = None
