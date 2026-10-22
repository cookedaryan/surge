"""Contract C10 ownership map and its CI check."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
REGION_OWNED = {"optimisation-python/app/algorithms/wtg_grouping.py"}


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_ownership", REPO_ROOT / "scripts" / "ci" / "check_ownership.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


def _repository_files() -> list[str]:
    roots = ["optimisation-python/app", "optimisation-python/tests", "web-map-next/src"]
    files = []
    for root in roots:
        for path in (REPO_ROOT / root).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                files.append(path.relative_to(REPO_ROOT).as_posix())
    return files


def _owners(path: str) -> set[str]:
    return {
        level
        for level in checker.LEVELS
        if checker.matches(
            checker.load_patterns(checker.OWNERSHIP_DIR / f"{level}.globs"), path
        )
    }


def test_only_region_owned_files_have_two_owners() -> None:
    shared = {path for path in _repository_files() if len(_owners(path)) > 1}
    assert shared == REGION_OWNED
    assert _owners(next(iter(REGION_OWNED))) == {"L2", "L3"}


@pytest.mark.parametrize(
    ("path", "level"),
    [
        ("optimisation-python/app/optimisation/deadline_guard.py", "L2"),
        ("optimisation-python/app/optimisation/search_activation.py", "L2"),
        ("optimisation-python/app/presentation/design_truth.py", "L2"),
        ("optimisation-python/app/presentation/search_evidence.py", "L2"),
        ("optimisation-python/app/evidence/fingerprints/topology.py", "L2"),
        ("optimisation-python/app/optimisation/cancellation.py", "L3"),
        ("optimisation-python/app/optimisation/profiles/resolve.py", "L3"),
        ("optimisation-python/app/presentation/explanation.py", "L3"),
        ("optimisation-python/app/presentation/profile_echo.py", "L3"),
        ("optimisation-python/app/evidence/fingerprints/geometry.py", "L3"),
        ("optimisation-python/app/evidence/fingerprints/final_design.py", "L3"),
        ("optimisation-python/app/evidence/cohort.py", "L3"),
        ("optimisation-python/app/api/v1/endpoints/runs.py", "L3"),
        ("optimisation-python/app/api/v1/endpoints/profiles.py", "L3"),
        ("optimisation-python/app/contracts/metric_registry_version.py", "L3"),
        ("web-map-next/src/features/optimization/ClaimDisclosure.tsx", "L1"),
        ("web-map-next/src/features/optimization/ResultsSheet.tsx", "L2"),
    ],
)
def test_each_stage0_stub_is_owned_by_the_level_that_implements_it(
    path: str, level: str
) -> None:
    assert (REPO_ROOT / path).exists()
    assert _owners(path) == {level}
    assert checker.violations(level, [path]) == []


@pytest.mark.parametrize(
    "path",
    [
        "contracts/codes.json",
        "optimisation-python/app/contracts/codes.py",
        "optimisation-python/app/schemas/optimise.py",
        "optimisation-python/app/schemas/legacy_mapping.py",
        "optimisation-python/app/api/v1/endpoints/optimise.py",
        "optimisation-python/app/optimisation/run_guard.py",
        "optimisation-python/app/optimisation/workflow_models.py",
        "optimisation-python/app/core/config.py",
    ],
)
def test_frozen_paths_fail_for_every_level(path: str) -> None:
    assert (REPO_ROOT / path).exists()
    for level in checker.LEVELS:
        assert checker.violations(level, [path])


def test_unowned_path_is_reported() -> None:
    problems = checker.violations(
        "L1", ["optimisation-python/app/optimisation/scoring.py"]
    )
    assert problems == [
        "optimisation-python/app/optimisation/scoring.py: not owned by L1"
    ]


def test_glob_semantics() -> None:
    assert checker.matches([(False, "a/**")], "a/b/c.py")
    assert checker.matches([(False, "a/**/c.py")], "a/c.py")
    assert not checker.matches([(False, "a/*.py")], "a/b/c.py")
    assert not checker.matches([(False, "a/**"), (True, "a/b.py")], "a/b.py")
