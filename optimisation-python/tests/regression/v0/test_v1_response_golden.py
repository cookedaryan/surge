"""WP3-2 — Characterise omitted-profile V1 = V0.

Posts every V0 fixture to ``POST /api/v1/optimise`` with the deployment
defaults (neither C5 flag set) and no ``profile`` in the request, then compares
the response with the golden captured at ``demo-opt-base``:

- **Exact match** for IDs, fingerprints, statuses, counts, strings, booleans
  and integers.
- **Tolerance match** (``DEFAULT_FLOAT_TOLERANCE``) for floats.
- **Ignored** per C2 (``app.contracts.response``): the additive blocks and the
  ``golden_comparison_exclusions``, plus the ``_provenance`` metadata key.

On ``demo-opt-base`` these tests pass trivially.  Their value comes at merge
time: every later package PR must keep them green.  A package that changes a
V0 value needs a CCR amending C12 or C2 and a re-captured golden.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.contracts.response import ADDITIVE_RESPONSE_BLOCKS
from tests.regression.v0.v0_harness import (
    FLAGS_UNSET,
    GOLDEN_DIR,
    PROVENANCE_KEY,
    V0_FIXTURES,
    cached_runner,
    collect_differences,
    fixture_id,
    load_golden,
    load_request,
)

Runner = Callable[[Path], dict[str, Any]]


@pytest.fixture(scope="module")
def v1_response() -> Runner:
    return cached_runner(FLAGS_UNSET)


def test_fixture_set_is_complete() -> None:
    """Both demo projects and at least the five audited SYN corpus fixtures."""
    names = {fixture.stem for fixture in V0_FIXTURES}
    assert {"constraint_demo_project_v2", "mvp_demo_project_v2"} <= names
    assert len([n for n in names if n.startswith("SYN-")]) >= 5
    assert all(fixture.exists() for fixture in V0_FIXTURES)


def test_every_golden_has_a_fixture() -> None:
    """A golden whose fixture was removed must not linger unchecked."""
    fixture_names = {fixture.stem for fixture in V0_FIXTURES}
    for golden in GOLDEN_DIR.glob("*.golden.json"):
        assert golden.name.removesuffix(".golden.json") in fixture_names, golden


@pytest.mark.parametrize("fixture", V0_FIXTURES, ids=fixture_id)
class TestV1ResponseGolden:
    def test_request_omits_profile(self, fixture: Path) -> None:
        assert "profile" not in load_request(fixture)

    def test_response_matches_golden(self, fixture: Path, v1_response: Runner) -> None:
        diffs = collect_differences(load_golden(fixture), v1_response(fixture))
        assert not diffs, (
            f"V0 golden mismatch for {fixture.stem} ({len(diffs)} differences):\n"
            + "\n".join(diffs[:20])
        )

    def test_golden_has_provenance(self, fixture: Path) -> None:
        provenance = load_golden(fixture).get(PROVENANCE_KEY)
        assert provenance is not None, "Golden must contain provenance metadata"
        assert {"base_sha", "captured_at", "fixture"} <= set(provenance)

    def test_golden_has_no_additive_blocks(self, fixture: Path) -> None:
        golden = load_golden(fixture)
        for block in ADDITIVE_RESPONSE_BLOCKS:
            assert block not in golden, f"V0 golden contains additive '{block}'"
