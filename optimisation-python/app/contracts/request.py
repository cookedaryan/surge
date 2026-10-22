"""Additive V1 request contract (C1).

Absent fields mean V0 behaviour. An explicit but unsupported value is rejected
with a ``ContractErrorCode``; it never silently falls back.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# Largest V1 request body the optimiser accepts, in bytes.
MAX_V1_REQUEST_BYTES = 10 * 1024 * 1024

# Generation settings Java may send alongside a profile. Empty until a profile
# definition declares one; browser clients may send none of these.
JAVA_GENERATION_SETTING_KEYS: tuple[str, ...] = ()


class ProfileSelection(BaseModel):
    """``OptimisationRequest.profile``: an allow-listed profile ID and version."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)


class CanonicalFeatureType(StrEnum):
    """Typed identity of an avoidance feature, independent of routing class."""

    ROAD = "road"
    HT_LINE = "ht_line"
    WATERCOURSE = "watercourse"
    PARCEL = "parcel"
    FOREST = "forest"
    PROTECTED_AREA = "protected_area"
    ENVIRONMENTAL = "environmental"
    WATER_BODY = "water_body"
    SETTLEMENT = "settlement"
    AVIATION = "aviation"
    RESTRICTED_AREA = "restricted_area"


class RoutingMode(StrEnum):
    """Existing ``routing_mode`` values. An enum, not a ``Literal``: typing caches
    Literals regardless of value order, which makes exported schemas unstable."""

    SOFT = "soft"
    HARD = "hard"


class TypedFeatureIdentity(BaseModel):
    """Additive properties on each ``avoidance_geojson`` feature.

    ``constraint_type`` keeps selecting routing treatment exactly as today.
    ``source_id`` is the stable upstream identity (the cadastral ``parcel_id``
    for parcels, the persisted asset id otherwise). ``feature_type`` is the
    typed identity used by land and environment metrics. ``routing_mode``
    already exists and is restated here because metrics consume it too.
    """

    model_config = ConfigDict(extra="ignore")

    source_id: str | None = Field(default=None, min_length=1)
    feature_type: CanonicalFeatureType | None = None
    routing_mode: RoutingMode | None = None
