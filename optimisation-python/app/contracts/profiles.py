"""Profile allow-list and definition-file shape (C6).

Python owns profile definitions; Java holds only these IDs and versions plus the
expected definition hash. ``contracts/profiles/allow-list.json`` is exported from
this module. Definition *values* are placeholders until the FRZ-1 policy freeze.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.canonical_json import canonical_sha256
from app.contracts.codes import MetricDirection, ProfilePolicyMode


class ProfileId(StrEnum):
    MINIMUM_COST = "minimum_cost"
    MINIMUM_LAND_IMPACT = "minimum_land_impact"
    MINIMUM_ENVIRONMENTAL_IMPACT = "minimum_environmental_impact"
    BALANCED = "balanced"


# The V1 ``scenario`` label each profile must be sent with.
PROFILE_SCENARIO_LABELS: dict[ProfileId, str] = {
    ProfileId.MINIMUM_COST: "Minimum Cost",
    ProfileId.MINIMUM_LAND_IMPACT: "Minimum Land Impact",
    ProfileId.MINIMUM_ENVIRONMENTAL_IMPACT: "Minimum Environmental Impact",
    ProfileId.BALANCED: "Balanced",
}

# Versions a client may request. A version leaves this set only by a contract
# change request; unknown explicit versions are rejected, never defaulted.
ALLOWED_PROFILE_VERSIONS: dict[ProfileId, tuple[str, ...]] = {
    profile_id: ("1",) for profile_id in ProfileId
}

DecimalString = str


class MetricTerm(BaseModel):
    """One scored metric inside a profile definition."""

    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1)
    direction: MetricDirection
    weight: DecimalString = Field(pattern=r"^\d+(\.\d+)?$")
    reference_min: DecimalString = Field(pattern=r"^-?\d+(\.\d+)?$")
    reference_max: DecimalString = Field(pattern=r"^-?\d+(\.\d+)?$")
    lexicographic_rank: int | None = Field(default=None, ge=1)
    tolerance: DecimalString | None = Field(default=None, pattern=r"^\d+(\.\d+)?$")


class ProfileDefinition(BaseModel):
    """The FRZ-1 values format. Decimals are strings so hashing is exact."""

    model_config = ConfigDict(extra="forbid")

    profile_id: ProfileId
    version: str = Field(min_length=1)
    policy_mode: ProfilePolicyMode
    terms: list[MetricTerm] = Field(min_length=1)
    tie_breaks: list[str] = Field(default_factory=list)
    generation_settings: dict[str, str] = Field(default_factory=dict)
    placeholder: bool = True


class ProfileDefinitionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    definitions: list[ProfileDefinition] = Field(min_length=1)


def definition_set_hash(definition_set: ProfileDefinitionSet) -> str:
    """Hash every definition in a stable order (the handshake value)."""
    ordered = sorted(
        definition_set.definitions,
        key=lambda item: (item.profile_id.value, item.version),
    )
    return canonical_sha256(
        {"definitions": [item.model_dump(mode="json") for item in ordered]}
    )
