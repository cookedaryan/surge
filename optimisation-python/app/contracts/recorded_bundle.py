"""Recorded Demo bundle manifest and frontend mode names (C8).

The bundle is validated and served by Java (WP6B). The manifest lives here so
the evidence runner and Java agree on one shape; Java mirrors it.
"""

from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

RECORDED_BUNDLE_SCHEMA_VERSION: Final = "1.0.0"


class DemoMode(StrEnum):
    """Frontend result-source states. Switching always passes through CLEARING."""

    LIVE = "LIVE"
    CLEARING = "CLEARING"
    RECORDED = "RECORDED"


class BundleHashes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_sha256: dict[str, str] = Field(min_length=1)
    profile_definition_sha256: str
    code_revisions: dict[str, str] = Field(min_length=1)
    image_digests: dict[str, str] = Field(min_length=1)
    catalogue_sha256: str
    response_schema_version: str
    evidence_schema_version: str


class RecordedBundleManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = RECORDED_BUNDLE_SCHEMA_VERSION
    bundle_id: str = Field(min_length=1)
    recorded_at: str = Field(min_length=1)
    release_candidate_tag: str = Field(min_length=1)
    hashes: BundleHashes
    winner_final_design_fingerprints: dict[str, str] = Field(min_length=1)
    cohort_hash: str | None
    on_screen_label: str = Field(min_length=1)
