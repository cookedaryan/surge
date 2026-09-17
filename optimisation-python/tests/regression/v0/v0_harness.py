"""Shared harness for the V0 golden tests (WP3-2, WP4-2) and their capture.

Goldens are produced and checked through the real ``POST /api/v1/optimise``
endpoint, so the C5 flags, the profile and search resolvers and the response
hooks all sit on the path that later packages change.  Calling the
orchestrator directly would skip every one of them.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.contracts.response import (
    ADDITIVE_RESPONSE_BLOCKS,
    GOLDEN_COMPARISON_EXCLUSIONS,
)
from app.core.config import get_settings
from app.main import app

# ── Paths ───────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[3]  # optimisation-python/
FIXTURES_DIR = ROOT / "tests" / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "v0_golden"

# The WP3-2 fixture set: the two demo projects and every corpus/SYN-* fixture.
V0_FIXTURES: tuple[Path, ...] = (
    FIXTURES_DIR / "constraint_demo_project_v2.json",
    FIXTURES_DIR / "mvp_demo_project_v2.json",
    *sorted((FIXTURES_DIR / "corpus").glob("SYN-*.json")),
)

V1_OPTIMISE_PATH = "/api/v1/optimise"

# Metadata key added by the capture script; not part of the response.
PROVENANCE_KEY = "_provenance"

# Default tolerance for floating-point comparisons (draft 0.6 §8).
DEFAULT_FLOAT_TOLERANCE: float = 1e-9

# ── C5 flag environments ────────────────────────────────────────────────────

PROFILES_FLAG_ENV = "SURGE_PROFILES_ENABLED"
SEARCH_FLAG_ENV = "SURGE_SEARCH_ENABLED"

# Deployment defaults: neither key set.
FLAGS_UNSET: Mapping[str, str | None] = {
    PROFILES_FLAG_ENV: None,
    SEARCH_FLAG_ENV: None,
}
# Both keys explicitly false (WP4-2).
FLAGS_OFF: Mapping[str, str | None] = {
    PROFILES_FLAG_ENV: "false",
    SEARCH_FLAG_ENV: "false",
}


# ── Fixtures and goldens ────────────────────────────────────────────────────


def fixture_id(fixture: Path) -> str:
    return fixture.stem


def golden_path(fixture: Path) -> Path:
    return GOLDEN_DIR / f"{fixture.stem}.golden.json"


def load_golden(fixture: Path) -> dict[str, Any]:
    path = golden_path(fixture)
    if not path.exists():
        pytest.fail(
            f"No V0 golden for {fixture.name}. Capture it with "
            "`python -m tests.regression.v0.capture_v0_golden`."
        )
    with open(path, encoding="utf-8") as f:
        golden: dict[str, Any] = json.load(f)
    return golden


def load_request(fixture: Path) -> dict[str, Any]:
    """Load a fixture as a V1 request, adding the V1-only mandatory fields."""
    with open(fixture, encoding="utf-8") as f:
        payload: dict[str, Any] = json.load(f)
    payload.setdefault("scenario", "Balanced")
    payload.setdefault("request_id", f"GOLDEN-{fixture.stem}")
    payload.setdefault("project_id", f"GOLDEN-{fixture.stem}")
    return payload


# ── Running the endpoint ────────────────────────────────────────────────────


def run_v1(fixture: Path, env: Mapping[str, str | None]) -> dict[str, Any]:
    """POST a fixture to the V1 endpoint with the given C5 environment."""
    with pytest.MonkeyPatch.context() as mp:
        for key, value in env.items():
            if value is None:
                mp.delenv(key, raising=False)
            else:
                mp.setenv(key, value)
        get_settings.cache_clear()
        try:
            response = TestClient(app).post(
                V1_OPTIMISE_PATH, json=load_request(fixture)
            )
        finally:
            get_settings.cache_clear()

    if response.status_code != 200:
        raise AssertionError(
            f"{V1_OPTIMISE_PATH} returned {response.status_code} for "
            f"{fixture.name}: {response.text[:500]}"
        )
    body: dict[str, Any] = response.json()
    return body


def cached_runner(
    env: Mapping[str, str | None],
) -> Callable[[Path], dict[str, Any]]:
    """Return a runner that calls the endpoint once per fixture."""
    cache: dict[Path, dict[str, Any]] = {}

    def run(fixture: Path) -> dict[str, Any]:
        if fixture not in cache:
            cache[fixture] = run_v1(fixture, env)
        return cache[fixture]

    return run


# ── Comparison ──────────────────────────────────────────────────────────────

_LIST_INDEX = re.compile(r"\[\d+\]")


def is_excluded_path(path: str) -> bool:
    """Whether a response path is ignored under contract C2.

    C2 additive blocks are ignored whole; ``golden_comparison_exclusions``
    use ``[]`` for any list index.
    """
    if path.split(".", 1)[0].split("[", 1)[0] in ADDITIVE_RESPONSE_BLOCKS:
        return True
    return _LIST_INDEX.sub("[]", path) in GOLDEN_COMPARISON_EXCLUSIONS


def collect_differences(
    expected: Any,
    actual: Any,
    path: str = "",
    tolerance: float = DEFAULT_FLOAT_TOLERANCE,
) -> list[str]:
    """Compare two JSON values and describe every difference.

    Strings, booleans, integers and nulls must match exactly; floats match
    within ``tolerance``.
    """
    if path and is_excluded_path(path):
        return []

    if isinstance(expected, dict) and isinstance(actual, dict):
        diffs: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            if key == PROVENANCE_KEY and not path:
                continue
            child = f"{path}.{key}" if path else key
            if is_excluded_path(child):
                continue
            if key not in expected:
                diffs.append(f"EXTRA key at {child}")
            elif key not in actual:
                diffs.append(f"MISSING key at {child}")
            else:
                diffs.extend(
                    collect_differences(expected[key], actual[key], child, tolerance)
                )
        return diffs

    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [
                f"LIST length at {path}: expected {len(expected)}, got {len(actual)}"
            ]
        diffs = []
        for i, (e, a) in enumerate(zip(expected, actual, strict=True)):
            diffs.extend(collect_differences(e, a, f"{path}[{i}]", tolerance))
        return diffs

    if _is_float_pair(expected, actual):
        if math.isnan(expected) and math.isnan(actual):
            return []
        if math.isclose(expected, actual, rel_tol=tolerance, abs_tol=tolerance):
            return []
        return [
            f"FLOAT at {path}: expected {expected}, got {actual} "
            f"(diff={abs(expected - actual)}, tol={tolerance})"
        ]

    if type(expected) is not type(actual) or expected != actual:
        return [f"VALUE at {path}: expected {expected!r}, got {actual!r}"]
    return []


def _is_float_pair(expected: Any, actual: Any) -> bool:
    """Both numbers, not booleans, and at least one of them a float."""
    numbers = (int, float)
    if isinstance(expected, bool) or isinstance(actual, bool):
        return False
    if not (isinstance(expected, numbers) and isinstance(actual, numbers)):
        return False
    return isinstance(expected, float) or isinstance(actual, float)
