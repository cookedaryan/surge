"""WP4-2 — Characterise search-off legacy behaviour.

Posts the WP3-2 fixtures to ``POST /api/v1/optimise`` with both C5 keys
explicitly false (``SURGE_PROFILES_ENABLED=false``,
``SURGE_SEARCH_ENABLED=false``).  The endpoint reads them through
``get_settings()``, so the flags reach the profile and search resolvers and
the response context.

Asserts:
- The response matches the WP3-2 golden.
- No ``search_evidence`` block, and no other C2 additive block, is present.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.contracts.response import ADDITIVE_RESPONSE_BLOCKS
from app.core.config import Settings
from tests.regression.v0.v0_harness import (
    FLAGS_OFF,
    PROFILES_FLAG_ENV,
    SEARCH_FLAG_ENV,
    V0_FIXTURES,
    cached_runner,
    collect_differences,
    fixture_id,
    load_golden,
)

Runner = Callable[[Path], dict[str, Any]]


@pytest.fixture(scope="module")
def flags_off_response() -> Runner:
    return cached_runner(FLAGS_OFF)


@pytest.mark.parametrize("fixture", V0_FIXTURES, ids=fixture_id)
class TestSearchOffGolden:
    def test_flags_off_matches_golden(
        self, fixture: Path, flags_off_response: Runner
    ) -> None:
        diffs = collect_differences(load_golden(fixture), flags_off_response(fixture))
        assert not diffs, (
            f"Search-off response differs from V0 golden for {fixture.stem} "
            f"({len(diffs)} differences):\n" + "\n".join(diffs[:20])
        )

    def test_no_search_evidence_block(
        self, fixture: Path, flags_off_response: Runner
    ) -> None:
        assert "search_evidence" not in flags_off_response(fixture)

    def test_no_additive_blocks(
        self, fixture: Path, flags_off_response: Runner
    ) -> None:
        response = flags_off_response(fixture)
        present = [block for block in ADDITIVE_RESPONSE_BLOCKS if block in response]
        assert not present, f"C2 additive blocks present with flags off: {present}"


class TestC5FlagKeys:
    """The environment keys these tests set are the ones Settings reads."""

    @pytest.mark.parametrize(("raw", "expected"), [("true", True), ("false", False)])
    def test_env_keys_drive_settings(
        self, monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
    ) -> None:
        monkeypatch.setenv(PROFILES_FLAG_ENV, raw)
        monkeypatch.setenv(SEARCH_FLAG_ENV, raw)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.surge_profiles_enabled is expected
        assert settings.surge_search_enabled is expected
        assert settings.new_generation_schedule_enabled is expected

    def test_flags_default_to_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(PROFILES_FLAG_ENV, raising=False)
        monkeypatch.delenv(SEARCH_FLAG_ENV, raising=False)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.surge_profiles_enabled is False
        assert settings.surge_search_enabled is False
        assert settings.new_generation_schedule_enabled is False
