"""WP5-3: ``group_wtgs(feeder_count=...)`` asks for exactly that many feeders."""

from typing import Any

import pytest

import app.algorithms.wtg_grouping as grouping_module
from app.algorithms.solver_models import SolverOptions
from app.algorithms.wtg_grouping import (
    FeederGroupingResult,
    GroupingObjective,
    group_wtgs,
)
from tests.test_scenarios import _make_diverse_project

CAPACITY_MW = 30.0  # 12 turbines x 5 MW: the minimum is 2 feeders


def _assert_capacity_valid(result: FeederGroupingResult, feeders: int) -> None:
    assert result.feeder_count == feeders
    assigned = [t for a in result.assignments for t in a.turbine_ids]
    assert sorted(assigned) == sorted(
        t.turbine_id for t in _make_diverse_project().turbines
    )
    assert all(a.turbine_ids for a in result.assignments)
    assert all(a.total_capacity_mw <= CAPACITY_MW for a in result.assignments)


def test_no_override_keeps_the_minimum_capacity_feasible_count() -> None:
    project = _make_diverse_project()
    default = group_wtgs(project, CAPACITY_MW)
    assert default.feeder_count == 2
    assert group_wtgs(project, CAPACITY_MW, feeder_count=None) == default
    assert group_wtgs(project, CAPACITY_MW, feeder_count=2) == default


@pytest.mark.parametrize("objective", list(GroupingObjective))
def test_override_returns_exactly_k_plus_one_capacity_valid_feeders(
    objective: GroupingObjective,
) -> None:
    project = _make_diverse_project()
    result = group_wtgs(project, CAPACITY_MW, objective=objective, feeder_count=3)
    _assert_capacity_valid(result, 3)
    assert [run.feeder_count for run in result.solver_runs] == [3]
    assert group_wtgs(project, CAPACITY_MW, objective=objective, feeder_count=3) == (
        result
    )


def test_override_below_the_capacity_bound_solves_nothing_and_returns_no_grouping() -> (
    None
):
    result = group_wtgs(_make_diverse_project(), CAPACITY_MW, feeder_count=1)
    assert result.assignments == ()
    assert result.feeder_count == 0
    assert result.solver_runs == ()


def test_override_equal_to_the_turbine_count_gives_one_turbine_per_feeder() -> None:
    result = group_wtgs(_make_diverse_project(), CAPACITY_MW, feeder_count=12)
    _assert_capacity_valid(result, 12)


@pytest.mark.parametrize("feeder_count", [13, 0, -1, True, 3.0])
def test_invalid_override_is_rejected(feeder_count: Any) -> None:
    with pytest.raises(ValueError):
        group_wtgs(_make_diverse_project(), CAPACITY_MW, feeder_count=feeder_count)


def test_a_solve_that_leaves_a_feeder_empty_is_not_substituted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def two_of_three(
        coords: list[tuple[float, float]], *args: Any, **kwargs: Any
    ) -> tuple[list[int], None]:
        return [index % 2 for index in range(len(coords))], None

    monkeypatch.setattr(grouping_module, "_solve_milp_assignment", two_of_three)
    result = group_wtgs(_make_diverse_project(), CAPACITY_MW, feeder_count=3)
    assert result.assignments == ()


def test_solver_options_pass_through_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[SolverOptions | None] = []
    original = grouping_module._solve_milp_assignment

    def capture(*args: Any) -> Any:
        seen.append(args[-1])
        return original(*args)

    monkeypatch.setattr(grouping_module, "_solve_milp_assignment", capture)
    options = SolverOptions(time_limit_s=5.0, node_limit=500)
    group_wtgs(
        _make_diverse_project(), CAPACITY_MW, feeder_count=3, solver_options=options
    )
    assert seen and all(value is options for value in seen)
